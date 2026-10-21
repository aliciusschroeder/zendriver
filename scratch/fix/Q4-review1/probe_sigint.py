"""SIGINT to the python process only, shortly after Chrome is spawned."""

import asyncio
import os
import shutil
import signal
import sys
import threading
import time

import zendriver as zd
from zendriver.core import util

delay = float(sys.argv[1]) if len(sys.argv) > 1 else 0.1
spawned = []
orig = util._start_process


def spy(*a, **k):
    p = orig(*a, **k)
    spawned.append(p)
    threading.Timer(delay, os.kill, (os.getpid(), signal.SIGINT)).start()
    return p


util._start_process = spy


def profile_of(p):
    for arg in p.args:
        if str(arg).startswith("--user-data-dir="):
            return str(arg).split("=", 1)[1]
    return None


async def main():
    b = await zd.start(headless=True)
    await asyncio.sleep(10)
    await b.stop()


t0 = time.monotonic()
try:
    asyncio.run(main())
    outcome = "returned"
except BaseException as e:
    outcome = type(e).__name__
elapsed = time.monotonic() - t0
for p in spawned:
    prof = profile_of(p)
    print(
        f"sigint@{delay} py{sys.version.split()[0]}: outcome={outcome} elapsed={elapsed:.2f}s "
        f"rc={p.poll()} profile_exists={os.path.exists(prof)} "
        f"registered={len(util.get_registered_instances())}",
        flush=True,
    )
    if p.poll() is None:
        p.kill()
        p.wait()
    shutil.rmtree(prof, ignore_errors=True)
