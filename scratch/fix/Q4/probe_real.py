"""Real-Chromium probe: a cancelled or failed zd.start() must leave nothing behind."""

import asyncio
import os
import shutil
import sys
import time

import zendriver as zd
from zendriver.core import util

print("zendriver from", zd.__file__)

spawned = []
orig = util._start_process


def spy(*a, **k):
    p = orig(*a, **k)
    spawned.append(p)
    return p


util._start_process = spy


def profile_of(p):
    for arg in p.args:
        if str(arg).startswith("--user-data-dir="):
            return str(arg).split("=", 1)[1]
    return None


async def hang(self):
    await asyncio.sleep(60)


async def boom(self):
    raise RuntimeError("simulated failure")


async def case(name, timeout, patch=None):
    spawned.clear()
    saved = None
    if patch:
        attr, fn = patch
        saved = getattr(zd.Browser, attr)
        setattr(zd.Browser, attr, fn)
    t0 = time.monotonic()
    try:
        b = await asyncio.wait_for(zd.start(headless=True), timeout)
        outcome = "started"
    except BaseException as e:
        b = None
        outcome = type(e).__name__
    elapsed = time.monotonic() - t0
    if saved:
        setattr(zd.Browser, patch[0], saved)
    if b is not None:
        await b.stop()
    for p in spawned:
        prof = profile_of(p)
        print(
            f"{name}: outcome={outcome} elapsed={elapsed:.2f}s rc={p.poll()} "
            f"profile_exists={os.path.exists(prof)} registered={len(util.get_registered_instances())}"
        )
        if p.poll() is None:
            p.kill()
            p.wait()
        shutil.rmtree(prof, ignore_errors=True)
    util.get_registered_instances().clear()


async def main():
    for t in (0.05, 0.15, 0.25):
        await case(f"cancel@{t}", t)
    await case("baseline", 30)
    for attr in ("update_targets", "_wait_for_initial_tab", "_read_headless_user_agent"):
        await case(f"hang:{attr}", 3, (attr, hang))
        await case(f"raise:{attr}", 30, (attr, boom))


asyncio.run(main())
