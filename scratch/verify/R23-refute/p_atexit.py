"""Probe: atexit cleanup of a host/port-connected Browser left running at loop close."""
import asyncio
import gc
import os
import shutil
import subprocess
import sys
import tempfile
import urllib.request
import warnings

import zendriver as zd
from zendriver.core import util

warnings.simplefilter("always")
print("zendriver from", zd.__file__, "python", sys.version.split()[0])
SCRATCH = os.path.dirname(os.path.abspath(__file__))

port = util.free_port()
prof = tempfile.mkdtemp(prefix="r23prof_", dir=SCRATCH)
proc = subprocess.Popen(
    [shutil.which("chromium"), "--headless=new", "--no-sandbox",
     f"--remote-debugging-port={port}", f"--user-data-dir={prof}", "--no-first-run", "about:blank"],
    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
)

state = {}


async def main():
    for _ in range(100):
        try:
            urllib.request.urlopen(f"http://127.0.0.1:{port}/json/version", timeout=1).read()
            break
        except Exception:
            await asyncio.sleep(0.1)
    b = await zd.start(host="127.0.0.1", port=port)
    tab = await b.get("data:text/html,<p>x</p>")
    state["b"] = b
    state["tab"] = tab
    print("connected, stopped =", b.stopped, "connection open:", not b.connection.closed)
    orig = b._stop

    async def traced_stop():
        print("atexit: _stop called")
        await orig()

    b._stop = traced_stop  # instance patch, Browser has no metaclass


try:
    asyncio.run(main())
    b = state["b"]
    print("after asyncio.run: connection open (websocket attr set):", not b.connection.closed,
          "listener running:", bool(b.connection.listener and b.connection.listener.running))
    print("external chrome alive after loop close:", proc.poll() is None)
finally:
    if proc.poll() is None:
        proc.kill()
    proc.wait()
    shutil.rmtree(prof, ignore_errors=True)
state.clear()
gc.collect()
print("done")
