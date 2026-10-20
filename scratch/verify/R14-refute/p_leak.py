"""Browser-free probe for temp profile leaks on failed starts (A3.7 / B16.6)."""
import asyncio
import glob
import os
import socket
import tempfile
import time

import zendriver as zd
from zendriver.core import util

print("zendriver from:", zd.__file__)
T = tempfile.gettempdir()
print("tempdir:", T)


def uc():
    return sorted(glob.glob(os.path.join(T, "uc_*")))


def closed_port():
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    p = s.getsockname()[1]
    s.close()
    return p


async def main():
    # (a) bad executable path, 3 attempts as in a retry loop
    before = uc()
    for i in range(3):
        try:
            await asyncio.wait_for(zd.start(headless=True, browser_executable_path="/nonexistent/chrome"), 30)
        except FileNotFoundError as e:
            pass
    after = uc()
    new = sorted(set(after) - set(before))
    print("(a) bad exe: dirs leaked by 3 failed starts:", len(new), [os.listdir(d) for d in new])
    print("    registered instances:", len(util.get_registered_instances()))

    # (b) connect to an existing browser where nothing listens
    before = uc()
    port = closed_port()
    t0 = time.monotonic()
    try:
        await asyncio.wait_for(zd.start(host="127.0.0.1", port=port, browser_executable_path="/nonexistent/chrome"), 60)
    except Exception as e:
        print("(b) connect-existing failed after %.1fs: %s" % (time.monotonic() - t0, type(e).__name__),
              "Failed to connect" in str(e))
    after = uc()
    new = sorted(set(after) - set(before))
    print("(b) connect-existing: dirs leaked:", len(new), [os.listdir(d) for d in new])

    # (c) control: with config passed explicitly and sanity check that a successful connect_existing
    # path would clean up is covered elsewhere (needs browser).

    for d in uc():
        os.rmdir(d)
    print("leftover after cleanup:", uc())


asyncio.run(main())
