"""Probe: Browser connected through host/port (connect-existing)."""
import asyncio
import json
import os
import shutil
import subprocess
import sys
import tempfile
import urllib.request

import zendriver as zd
from zendriver.core import util

print("zendriver from", zd.__file__, "python", sys.version.split()[0])

SCRATCH = os.path.dirname(os.path.abspath(__file__))


def launch_chrome():
    port = util.free_port()
    prof = tempfile.mkdtemp(prefix="r23prof_", dir=SCRATCH)
    p = subprocess.Popen(
        [
            shutil.which("chromium"), "--headless=new", "--no-sandbox",
            f"--remote-debugging-port={port}", "--remote-debugging-host=127.0.0.1",
            f"--user-data-dir={prof}", "--no-first-run", "about:blank",
        ],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )
    return p, port, prof


async def wait_up(port):
    for _ in range(100):
        try:
            urllib.request.urlopen(f"http://127.0.0.1:{port}/json/version", timeout=1).read()
            return
        except Exception:
            await asyncio.sleep(0.1)
    raise RuntimeError("chrome did not come up")


async def main():
    proc, port, prof = launch_chrome()
    try:
        await wait_up(port)
        b = await zd.start(host="127.0.0.1", port=port)
        print("connected:", b.websocket_url, "stopped property:", b.stopped, "tabs:", len(b.tabs))
        tab = await b.get("data:text/html,<p>x</p>")
        print("browser usable:", await tab.evaluate("1+1"))

        # second start() on a live connected browser
        old = b.connection
        old_listener = old.listener
        print("old connection closed?", old.closed, "listener running?", old_listener and old_listener.running)
        import warnings
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            await asyncio.wait_for(b.start(), 30)
        print("warnings from second start():", [str(x.message) for x in w])
        print(
            "second start(): connection replaced:", b.connection is not old,
            "old still open:", not old.closed,
            "old listener running:", bool(old.listener and old.listener.running),
        )
        # usable after second start?
        tab2 = await asyncio.wait_for(b.get("data:text/html,<p>y</p>", new_tab=True), 30)
        print("usable after second start:", await tab2.evaluate("2+2"))

        # what does stop() do to the external browser? (it sends Browser.close)
        await b.stop()
        await asyncio.sleep(1)
        print("after stop(): old still open:", not old.closed,
              "old listener running:", bool(old.listener and old.listener.running),
              "external chrome alive:", proc.poll() is None)
        # clean the leaked connection ourselves
        if not old.closed:
            await old.aclose()
    finally:
        if proc.poll() is None:
            proc.kill()
        proc.wait()
        shutil.rmtree(prof, ignore_errors=True)


asyncio.run(main())
