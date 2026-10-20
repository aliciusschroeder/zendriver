"""Reproduce: undrained stderr PIPE -> Chrome blocks -> CDP hangs.

usage: probe_logging.py <mode>
  mode = evaluate : --enable-logging=stderr, console.log 2 KB via tab.evaluate
  mode = default  : default flags, same console spam (control)
"""
import asyncio
import fcntl
import os
import signal
import sys
import termios
import time
import struct

import zendriver as zd

print("zendriver from", zd.__file__, "python", sys.version.split()[0], flush=True)

MODE = sys.argv[1] if len(sys.argv) > 1 else "evaluate"
MAX_ITER = int(sys.argv[2]) if len(sys.argv) > 2 else 300


def pending(f):
    buf = fcntl.ioctl(f.fileno(), termios.FIONREAD, struct.pack("i", 0))
    return struct.unpack("i", buf)[0]


def descendants(pid):
    out = []
    kids = {}
    for d in os.listdir("/proc"):
        if not d.isdigit():
            continue
        try:
            with open(f"/proc/{d}/stat") as fh:
                st = fh.read()
            ppid = int(st.rsplit(")", 1)[1].split()[1])
            kids.setdefault(ppid, []).append(int(d))
        except Exception:
            pass
    stack = [pid]
    while stack:
        p = stack.pop()
        for c in kids.get(p, []):
            out.append(c)
            stack.append(c)
    return out


def wchans(pid):
    res = {}
    try:
        for t in os.listdir(f"/proc/{pid}/task"):
            try:
                w = open(f"/proc/{pid}/task/{t}/wchan").read().strip()
                comm = open(f"/proc/{pid}/task/{t}/comm").read().strip()
            except Exception:
                continue
            if "pipe" in w:
                res[f"{t}:{comm}"] = w
    except Exception as e:
        res["err"] = repr(e)
    return res


async def main():
    args = {"evaluate": ["--enable-logging=stderr"], "drain": ["--enable-logging=stderr"],
            "get": ["--enable-logging=stderr"], "v1": ["--enable-logging=stderr", "--v=1"],
            "default": []}[MODE]
    browser = await zd.start(headless=True, browser_args=args)
    proc = browser._process
    if MODE == "drain":
        import threading
        drained = [0]
        def drain():
            while True:
                b = os.read(proc.stderr.fileno(), 65536)
                if not b:
                    break
                drained[0] += len(b)
        threading.Thread(target=drain, daemon=True).start()
    pid = proc.pid
    print("browser pid", pid, "pipe size", fcntl.fcntl(proc.stderr.fileno(), 1032), flush=True)  # F_GETPIPE_SZ
    print("stderr pending after start", pending(proc.stderr), "stdout pending", pending(proc.stdout), flush=True)
    tab = browser.main_tab
    hung = False
    for i in range(MAX_ITER):
        if MODE in ("get", "v1"):
            async def step():
                await tab.get("data:text/html,<script>console.error('x'.repeat(200))</script>hi")
                return await tab.evaluate("1+1")
            t = asyncio.ensure_future(step())
        else:
            t = asyncio.ensure_future(tab.evaluate("console.log('x'.repeat(2000)); 1+1"))
        try:
            r = await asyncio.wait_for(asyncio.shield(t), 10)
        except asyncio.TimeoutError:
            print(f"iteration {i}: TIMEOUT after 10s; stderr pending={pending(proc.stderr)} alive={proc.poll() is None}", flush=True)
            print("stuck task stack:", flush=True)
            t.print_stack(file=sys.stdout)
            print("browser main threads blocked in pipe write:", wchans(pid), flush=True)
            for c in descendants(pid):
                w = wchans(c)
                if w:
                    print("  child", c, w, flush=True)
            hung = True
            t.cancel()
            break
        if i % 10 == 0:
            print(f"iteration {i}: ok r={r} stderr pending={pending(proc.stderr)}" + (f" drained={drained[0]}" if MODE == "drain" else ""), flush=True)
    else:
        print("no hang after", MAX_ITER, "iterations; stderr pending", pending(proc.stderr), flush=True)

    if hung:
        # second fresh CDP call: Browser.getVersion over the browser connection
        try:
            v = await asyncio.wait_for(browser.connection.send(zd.cdp.browser.get_version()), 10)
            print("Browser.getVersion answered", v[1] if isinstance(v, tuple) else v, flush=True)
        except asyncio.TimeoutError:
            print("Browser.getVersion TIMEOUT: browser process not answering", flush=True)
        try:
            await asyncio.wait_for(tab.evaluate("1+1"), 10)
            print("simple evaluate answered", flush=True)
        except asyncio.TimeoutError:
            print("simple evaluate 1+1 TIMEOUT", flush=True)
        # show that draining the pipe un-sticks Chrome (proves the cause)
        kids = descendants(pid)
        st = time.monotonic()
        stop_task = asyncio.ensure_future(browser.stop())
        try:
            await asyncio.wait_for(asyncio.shield(stop_task), 15)
            print(f"browser.stop() finished in {time.monotonic()-st:.1f}s", flush=True)
        except asyncio.TimeoutError:
            print("browser.stop() did not finish within 15s; stack:", flush=True)
            stop_task.print_stack(file=sys.stdout)
            # cleanup: kill only the processes this script started
            for p in [pid] + kids:
                try:
                    os.kill(p, signal.SIGKILL)
                except ProcessLookupError:
                    pass
            try:
                await asyncio.wait_for(stop_task, 15)
                print("stop() completed after SIGKILL", flush=True)
            except Exception as e:
                print("stop after kill:", type(e).__name__, e, flush=True)
    else:
        await browser.stop()
    left = [p for p in descendants(os.getpid())]
    print("leftover descendants of probe:", left, flush=True)


asyncio.run(main())
