"""B13.8: does the startup-failure path log Chrome's stderr when Chrome is still alive?

mode 'portbusy': the DevTools port is bound (not listening) by us, so Chrome cannot open it.
mode 'mockconn': like the repo test, test_connection is forced False (Chrome alive & healthy).
mode 'exits'   : Chrome exits immediately (bad flag that makes it exit) -> EOF case.
"""
import asyncio
import logging
import os
import socket
import sys
import time

import zendriver
import zendriver.core.util as zutil
from zendriver.core.browser import Browser

print("zendriver from", zendriver.__file__, sys.version.split()[0], flush=True)
MODE = sys.argv[1]

records = []
captured = []


class Cap(logging.Handler):
    def emit(self, r):
        records.append(r.getMessage())


logging.getLogger("zendriver").addHandler(Cap())
logging.getLogger("zendriver").setLevel(logging.DEBUG)

started_pids = []
orig_start_process = zutil._start_process


def spy_start_process(*a, **k):
    p = orig_start_process(*a, **k)
    started_pids.append(p)
    return p


zutil._start_process = spy_start_process

orig_read = zutil._read_process_stderr


async def spy_read(process, n=2 ** 16):
    alive = process.poll() is None
    import array, fcntl, termios
    buf = array.array("i", [0])
    fcntl.ioctl(process.stderr.fileno(), termios.FIONREAD, buf, True)
    print("before _read_process_stderr: chrome alive=%s, bytes waiting in pipe=%d" % (alive, buf[0]), flush=True)
    class Rec:
        def __init__(self, f): self.f = f
        def read(self, n):
            d = self.f.read(n); captured.append(d); return d
        def fileno(self): return self.f.fileno()
        def close(self): self.f.close()
    process.stderr = Rec(process.stderr)
    t = time.monotonic()
    r = await orig_read(process, n)
    print("_read_process_stderr returned %d chars in %.2fs" % (len(r), time.monotonic() - t), flush=True)
    return r


zutil._read_process_stderr = spy_read


async def main():
    s = None
    kwargs = {}
    if MODE == "portbusy":
        s = socket.socket()
        s.bind(("127.0.0.1", 0))
        port = s.getsockname()[1]
        zutil.free_port = lambda: port
        print("holding port", port, "bound but not listening", flush=True)
    elif MODE == "mockconn":
        async def never(self):
            return False
        Browser.test_connection = never
        kwargs = dict(browser_connection_max_tries=1, browser_connection_timeout=0.1)
    elif MODE == "rootsandbox":
        import zendriver.core.config as zc
        zc.is_root = lambda: False
        kwargs = dict(sandbox=True)
    t = time.monotonic()
    try:
        b = await asyncio.wait_for(zendriver.start(headless=True, **kwargs), 60)
        print("unexpectedly started", flush=True)
        await b.stop()
    except Exception as e:
        print("start failed after %.1fs: %s" % (time.monotonic() - t, str(e).strip().splitlines()[1] if "\n" in str(e) else e), flush=True)
    for m in records:
        if m.startswith("Browser stderr"):
            print("LOGGED:", m[:400].replace("\n", " | "), flush=True)
    for p in started_pids:
        print("chrome pid %d returncode %r" % (p.pid, p.poll()), flush=True)
        if p.poll() is None:
            p.kill(); p.wait()
    if s:
        s.close()
    await asyncio.sleep(0.5)
    for d in captured:
        txt = d.decode("utf-8", "replace")
        print("data the worker thread read later and threw away: %d bytes; devtools line present: %s" % (len(d), "Cannot start http server for devtools" in txt), flush=True)
        for line in txt.splitlines():
            if "devtools" in line.lower() or "root" in line.lower():
                print("   ", line[:200], flush=True)


asyncio.run(main())
