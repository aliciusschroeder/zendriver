"""Reviewer probe for Q4 with real Chromium.

modes:
  frozen   - SIGSTOP chrome inside update_targets, wait_for(start, 2)
  attach   - start a real browser A, attach browser B (host/port) and make B fail
             or be cancelled; A must survive and stay usable
  cancel   - wait_for(zd.start(headless=True), t) for several t
"""

import asyncio
import os
import shutil
import signal
import sys
import time

import zendriver as zd
from zendriver.core import util

print("zendriver from", zd.__file__, "python", sys.version.split()[0])

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


def report_and_clean(name, outcome, elapsed):
    for p in spawned:
        prof = profile_of(p)
        print(
            f"{name}: outcome={outcome} elapsed={elapsed:.2f}s rc={p.poll()} "
            f"profile_exists={os.path.exists(prof)} registered={len(util.get_registered_instances())}",
            flush=True,
        )
        if p.poll() is None:
            try:
                os.kill(p.pid, signal.SIGCONT)
            except ProcessLookupError:
                pass
            p.kill()
            p.wait()
        shutil.rmtree(prof, ignore_errors=True)
    spawned.clear()
    util.get_registered_instances().clear()


async def frozen():
    real_update = zd.Browser.update_targets

    async def freeze_then_update(self):
        os.kill(self._process.pid, signal.SIGSTOP)
        await real_update(self)

    zd.Browser.update_targets = freeze_then_update
    t0 = time.monotonic()
    try:
        await asyncio.wait_for(zd.start(headless=True), 2)
        outcome = "started"
    except BaseException as e:
        outcome = type(e).__name__
    elapsed = time.monotonic() - t0
    zd.Browser.update_targets = real_update
    report_and_clean("frozen", outcome, elapsed)


async def attach():
    a = await zd.start(headless=True)
    host, port = a.config.host, a.config.port
    print("browser A at", host, port, "pid", a._process.pid)
    real_update = zd.Browser.update_targets

    async def boom(self):
        if self is not a:
            raise RuntimeError("simulated failure in attached instance")
        await real_update(self)

    async def hang(self):
        if self is not a:
            await asyncio.sleep(60)
        await real_update(self)

    for name, patch, timeout in (("attach-raise", boom, 30), ("attach-cancel", hang, 1)):
        zd.Browser.update_targets = patch
        t0 = time.monotonic()
        try:
            await asyncio.wait_for(zd.start(host=host, port=port, headless=True), timeout)
            outcome = "started"
        except BaseException as e:
            outcome = type(e).__name__
        elapsed = time.monotonic() - t0
        zd.Browser.update_targets = real_update
        await asyncio.sleep(0.5)
        alive = a._process.poll() is None
        try:
            tab = await asyncio.wait_for(a.get("about:blank"), 5)
            usable = (await asyncio.wait_for(tab.evaluate("1+1"), 5)) == 2
        except BaseException as e:
            usable = f"no ({type(e).__name__})"
        others = [b for b in util.get_registered_instances() if b is not a]
        print(
            f"{name}: outcome={outcome} elapsed={elapsed:.2f}s A alive={alive} A usable={usable} "
            f"leftover registered={len(others)}",
            flush=True,
        )
    await a.stop()
    report_and_clean("attach-final", "-", 0)


async def cancel():
    for t in (0.05, 0.15, 0.25, 0.4):
        t0 = time.monotonic()
        try:
            b = await asyncio.wait_for(zd.start(headless=True), t)
            outcome = "started"
            await b.stop()
        except BaseException as e:
            outcome = type(e).__name__
        report_and_clean(f"cancel@{t}", outcome, time.monotonic() - t0)


if __name__ == "__main__":
    mode = sys.argv[1]
    asyncio.run({"frozen": frozen, "attach": attach, "cancel": cancel}[mode]())
