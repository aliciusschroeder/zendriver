"""B13.8: on a failed start with Chrome still alive, the stderr capture returns "".

mode = port   : real Chromium, DevTools port already bound by us -> Chrome cannot listen
mode = fake   : fake 'browser' script that writes a line to stderr and keeps running
mode = exits  : fake 'browser' script that writes a line to stderr and exits (control)
"""
import asyncio
import logging
import os
import socket
import stat
import sys
import threading
import time

import zendriver as zd
import zendriver.core.util as zutil

print("zendriver from", zd.__file__, "python", sys.version.split()[0], flush=True)
MODE = sys.argv[1] if len(sys.argv) > 1 else "port"
HERE = os.path.dirname(os.path.abspath(__file__))

records = []


class H(logging.Handler):
    def emit(self, r):
        records.append(r.getMessage())


logging.getLogger("zendriver").addHandler(H())
logging.getLogger("zendriver").setLevel(logging.DEBUG)


async def main():
    kwargs = dict(headless=True, browser_connection_max_tries=2, browser_connection_timeout=0.5)
    blocker = None
    if MODE == "port":
        blocker = socket.socket()
        blocker.bind(("127.0.0.1", 0))  # bound, not listening: Chrome's bind() gets EADDRINUSE
        port = blocker.getsockname()[1]
        zutil.free_port = lambda: port
        print("devtools port pre-bound:", port, flush=True)
    else:
        script = os.path.join(HERE, f"fakebrowser_{MODE}.sh")
        with open(script, "w") as fh:
            fh.write("#!/bin/sh\necho 'FATAL: fake browser could not start devtools' >&2\n")
            if MODE == "fake":
                fh.write("exec sleep 30\n")
            else:
                fh.write("exit 3\n")
        os.chmod(script, os.stat(script).st_mode | stat.S_IEXEC)
        kwargs["browser_executable_path"] = script

    orig = zutil._read_process_stderr

    async def wrapped(process, n=2**16):
        import fcntl, struct, termios
        before = struct.unpack("i", fcntl.ioctl(process.stderr.fileno(), termios.FIONREAD, struct.pack("i", 0)))[0]
        res = await orig(process, n)
        print(f"_read_process_stderr: {before} bytes waiting in pipe, process alive={process.poll() is None}, returned {res[:120]!r}", flush=True)
        return res

    zutil._read_process_stderr = wrapped
    st = time.monotonic()
    try:
        b = await asyncio.wait_for(zd.start(**kwargs), 60)
        print("unexpected: started", b, flush=True)
        await b.stop()
    except Exception as e:
        print(f"start failed after {time.monotonic()-st:.1f}s: {str(e).strip().splitlines()[1] if str(e).strip() else type(e).__name__}", flush=True)
    for m in records:
        if m.startswith("Browser stderr") or "Timeout reading" in m:
            print("LOGGED:", m[:400].replace("\n", " | "), flush=True)
    print("threads alive after start() returned:", [t.name for t in threading.enumerate()], flush=True)
    if blocker:
        blocker.close()


asyncio.run(main())
