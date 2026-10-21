"""
real chromium probes of Browser.stop() on the fix branch. usage: probe_real.py MODE
modes run inside asyncio.run; the parent (driver) checks pid/profile after exit.
"""

import asyncio
import os
import signal
import sys
import time

import zendriver as zd

MODE = sys.argv[1]


def info(*a: object) -> None:
    print(*a, flush=True)


async def main() -> None:
    info("zendriver", zd.__file__, sys.version.split()[0])
    b = await zd.start(headless=True)
    pid = b._process_pid
    udd = b.config.user_data_dir
    info("PID", pid)
    info("UDD", udd)
    tab = await b.get("about:blank")
    await tab.evaluate("1")
    for _ in range(2):
        t = await b.get("about:blank", new_tab=True)
        await t.evaluate("1")

    if MODE == "sigstop_stop":
        os.kill(pid, signal.SIGSTOP)
        t0 = time.monotonic()
        task = asyncio.create_task(b.stop())
        done, _ = await asyncio.wait({task}, timeout=60)
        info("stop done", bool(done), "elapsed %.1f" % (time.monotonic() - t0))
        if done:
            info("stop exc", task.exception())
        else:
            task.print_stack()
            os.kill(pid, signal.SIGKILL)
        info("proc alive after stop", _alive(pid), "profile exists", os.path.exists(udd))
    elif MODE == "sigstop_waitfor":
        # user bounds stop(); the atexit fallback must finish the job
        os.kill(pid, signal.SIGSTOP)
        t0 = time.monotonic()
        try:
            await asyncio.wait_for(b.stop(), 3)
            info("stop returned")
        except asyncio.TimeoutError:
            info("wait_for(stop(), 3) timed out after %.1f" % (time.monotonic() - t0))
        info("proc alive before exit", _alive(pid))
    elif MODE == "kill_stop":
        b._process.kill()
        try:
            await b.stop()
            info("stop OK")
        except BaseException as e:
            info("stop RAISED", repr(e))
        info("_process", b._process, "profile exists", os.path.exists(udd))
    elif MODE == "noстоп" or MODE == "nostop":
        info("returning without stop()")
    elif MODE == "healthy":
        t0 = time.monotonic()
        await b.stop()
        info("healthy stop elapsed %.2f" % (time.monotonic() - t0))
        info("profile exists", os.path.exists(udd))
    elif MODE == "concurrent":
        r = await asyncio.gather(b.stop(), _later(b.stop(), 0.1), return_exceptions=True)
        info("results", r)
    elif MODE == "double_cancel_then_stop":
        # cancelled stop, then a second stop() must finish and unregister
        task = asyncio.create_task(b.stop())
        await asyncio.sleep(0.01)
        task.cancel()
        r = await asyncio.gather(task, return_exceptions=True)
        info("first", r)
        await b.stop()
        info("second stop OK; profile exists", os.path.exists(udd))


async def _later(coro, delay):  # type: ignore[no-untyped-def]
    await asyncio.sleep(delay)
    return await coro


def _alive(pid: int) -> bool:
    try:
        with open(f"/proc/{pid}/stat") as f:
            state = f.read().split(")")[-1].split()[0]
        return state != "Z"
    except FileNotFoundError:
        return False


t0 = time.monotonic()
asyncio.run(main())
info("asyncio.run returned after %.1f" % (time.monotonic() - t0))
