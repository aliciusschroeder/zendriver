"""Probe: does Chrome stall once its undrained stderr pipe fills?

usage: p1_console.py <args-mode> <drain:0|1> <rounds> <payload>
args-mode: none | logging | logging_v1
"""
import array
import asyncio
import fcntl
import os
import sys
import termios
import threading
import time

import zendriver
import psutil

print("zendriver from", zendriver.__file__, "python", sys.version.split()[0], flush=True)

MODE = sys.argv[1]
DRAIN = sys.argv[2] == "1"
ROUNDS = int(sys.argv[3])
PAYLOAD = int(sys.argv[4])

ARGS = {
    "none": [],
    "logging": ["--enable-logging=stderr"],
    "logging_v1": ["--enable-logging=stderr", "--v=1"],
}[MODE]


def pending(fobj) -> int:
    buf = array.array("i", [0])
    fcntl.ioctl(fobj.fileno(), termios.FIONREAD, buf, True)
    return buf[0]


def wchans(pid: int) -> dict:
    out = {}
    try:
        for tid in os.listdir(f"/proc/{pid}/task"):
            try:
                w = open(f"/proc/{pid}/task/{tid}/wchan").read()
                comm = open(f"/proc/{pid}/task/{tid}/comm").read().strip()
            except OSError:
                continue
            if "pipe" in w:
                out[f"{tid}:{comm}"] = w
    except OSError:
        pass
    return out


async def main() -> None:
    t0 = time.monotonic()
    b = await zendriver.start(headless=True, browser_args=ARGS)
    proc = b._process
    print("udd", b.config.user_data_dir, flush=True)
    pid = proc.pid
    print("started in %.1fs; stdout pending %d stderr pending %d" % (
        time.monotonic() - t0, pending(proc.stdout), pending(proc.stderr)), flush=True)
    drained = [0]
    if DRAIN:
        def drain():
            while True:
                d = os.read(proc.stderr.fileno(), 65536)
                if not d:
                    return
                drained[0] += len(d)
        threading.Thread(target=drain, daemon=True).start()
    tab = b.main_tab
    hung = False
    for i in range(ROUNDS):
        try:
            await asyncio.wait_for(
                tab.evaluate(
                    "for (let k=0;k<20;k++) console.log('x'.repeat(%d)); 1+1" % PAYLOAD
                ),
                10,
            )
        except asyncio.TimeoutError:
            print("round %d: evaluate TIMEOUT; stderr pending %d; stdout pending %d; alive=%s" % (
                i, pending(proc.stderr), pending(proc.stdout), proc.poll() is None), flush=True)
            print("  browser-proc threads in pipe wait:", wchans(pid), flush=True)
            hung = True
            break
        if i % 5 == 0:
            print("round %d ok; stderr pending %d drained %d" % (i, pending(proc.stderr), drained[0]), flush=True)
    if hung:
        # can the browser process answer anything?
        try:
            v = await asyncio.wait_for(b.connection.send(zendriver.cdp.browser.get_version()), 10)
            print("Browser.getVersion answered:", v[1] if isinstance(v, tuple) else v, flush=True)
        except asyncio.TimeoutError:
            print("Browser.getVersion TIMEOUT", flush=True)
        # Does draining the pipe un-wedge it?
        got = os.read(proc.stderr.fileno(), 65536)
        print("drained %d bytes after the hang; tail: %r" % (len(got), got[-200:]), flush=True)
        try:
            await asyncio.wait_for(tab.evaluate("1+1"), 10)
            print("after draining once: evaluate OK -> pipe was the cause", flush=True)
        except asyncio.TimeoutError:
            print("after draining once: evaluate still TIMEOUT", flush=True)
    else:
        print("no hang after %d rounds; stderr pending %d drained %d" % (ROUNDS, pending(proc.stderr), drained[0]), flush=True)
    ts = time.monotonic()
    try:
        await asyncio.wait_for(b.stop(), 30)
        print("stop ok in %.1fs" % (time.monotonic() - ts), flush=True)
    except asyncio.TimeoutError:
        print("stop TIMEOUT", flush=True)
        try:
            for c in psutil.Process(pid).children(recursive=True):
                c.kill()
        except psutil.Error:
            pass
        proc.kill()
        proc.wait()


asyncio.run(main())
