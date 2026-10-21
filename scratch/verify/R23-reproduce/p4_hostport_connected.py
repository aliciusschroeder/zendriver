"""R23 / A3.10, B16.13: Browser connected via host/port to an externally launched Chrome."""
import asyncio
import os
import shutil
import socket
import subprocess
import tempfile

import psutil
import zendriver as zd

print("zendriver from", zd.__file__)


def free_port():
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    p = s.getsockname()[1]
    s.close()
    return p


def my_ws_sockets(port):
    me = psutil.Process(os.getpid())
    return [c for c in me.net_connections(kind="tcp")
            if c.raddr and c.raddr.port == port and c.status == psutil.CONN_ESTABLISHED]


async def main(port):
    b = await zd.start(host="127.0.0.1", port=port)
    print("connected:", b.info.webSocketDebuggerUrl)
    print("B16.13 stopped property:", b.stopped, "| connection closed:", b.connection.closed,
          "| tabs:", len(b.tabs), "| _process:", b._process)
    # the conftest-style recreate check
    print("conftest check `browser is None or browser.stopped` ->", b is None or b.stopped)
    await asyncio.sleep(0.3)
    print("established sockets to chrome before 2nd start:", len(my_ws_sockets(port)))

    old = b.connection
    old_listener = old.listener
    r = await asyncio.wait_for(b.start(), 60)
    await asyncio.sleep(0.3)
    print("A3.10 second start(): returned same obj", r is b,
          "| connection replaced:", b.connection is not old,
          "| old still open:", not old.closed,
          "| old listener running:", bool(old_listener and old_listener.running))
    print("established sockets to chrome after 2nd start:", len(my_ws_sockets(port)))
    print("asyncio tasks alive:", len([t for t in asyncio.all_tasks() if not t.done()]))

    # what the asyncio_atexit hook does for this browser
    await b._atexit_cleanup()
    await asyncio.sleep(0.3)
    print("B16.13 after _atexit_cleanup(): connection closed:", b.connection.closed,
          "| old closed:", old.closed,
          "| established sockets:", len(my_ws_sockets(port)))

    # cleanup: close both connections explicitly (do not close the external Chrome via CDP)
    await old.aclose()
    await b.connection.aclose()
    for t in b.targets:
        await t.aclose()
    await asyncio.sleep(0.3)
    print("after explicit aclose of both: established sockets:", len(my_ws_sockets(port)))


port = free_port()
udd = tempfile.mkdtemp(prefix="r23-ext-", dir=os.path.dirname(os.path.abspath(__file__)))
proc = subprocess.Popen([
    shutil.which("chromium"), "--headless=new", "--no-sandbox", f"--user-data-dir={udd}",
    f"--remote-debugging-port={port}", "--remote-debugging-host=127.0.0.1", "about:blank",
], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
try:
    import time
    import urllib.request
    for _ in range(50):
        try:
            urllib.request.urlopen(f"http://127.0.0.1:{port}/json/version", timeout=1).read()
            break
        except Exception:
            time.sleep(0.2)
    asyncio.run(main(port))
finally:
    proc.terminate()
    try:
        proc.wait(10)
    except Exception:
        proc.kill()
        proc.wait()
    shutil.rmtree(udd, ignore_errors=True)
    print("external chrome stopped, rc", proc.returncode)
