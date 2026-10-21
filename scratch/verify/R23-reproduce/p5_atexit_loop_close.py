"""B16.13: at real loop close, the asyncio_atexit hook skips _stop() for a host/port browser."""
import asyncio
import os
import shutil
import socket
import subprocess
import tempfile
import time
import urllib.request

import zendriver as zd

print("zendriver from", zd.__file__)


def free_port():
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    p = s.getsockname()[1]
    s.close()
    return p


calls = []


async def main(port):
    b = await zd.start(host="127.0.0.1", port=port)
    orig = b._stop

    async def spy_stop():
        calls.append("_stop")
        # do not actually close the external chrome; just record the call
    b._stop = spy_stop
    print("connected, stopped =", b.stopped)
    return b


port = free_port()
udd = tempfile.mkdtemp(prefix="r23-ext-", dir=os.path.dirname(os.path.abspath(__file__)))
proc = subprocess.Popen([
    shutil.which("chromium"), "--headless=new", "--no-sandbox", f"--user-data-dir={udd}",
    f"--remote-debugging-port={port}", "about:blank",
], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
try:
    for _ in range(50):
        try:
            urllib.request.urlopen(f"http://127.0.0.1:{port}/json/version", timeout=1).read()
            break
        except Exception:
            time.sleep(0.2)
    b = asyncio.run(main(port))
    print("after loop close: atexit hook called _stop?", calls,
          "| connection.closed:", b.connection.closed)
finally:
    proc.terminate()
    try:
        proc.wait(10)
    except Exception:
        proc.kill()
        proc.wait()
    shutil.rmtree(udd, ignore_errors=True)
    print("external chrome stopped, rc", proc.returncode)
