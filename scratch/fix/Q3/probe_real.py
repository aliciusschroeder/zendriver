"""real chromium probes for group Q3, run against the worktree's zendriver"""

import asyncio
import os
import signal
import sys
import time

import psutil

import zendriver as zd

print("zendriver:", zd.__file__, flush=True)


def alive(pid: int) -> bool:
    try:
        return psutil.Process(pid).status() != psutil.STATUS_ZOMBIE
    except psutil.NoSuchProcess:
        return False


async def sigstop() -> None:
    b = await zd.start(headless=True)
    tab = await b.get("about:blank")
    await tab.evaluate("1")
    pid, udd = b._process_pid, b.config.user_data_dir
    assert pid
    os.kill(pid, signal.SIGSTOP)
    t0 = time.monotonic()
    task = asyncio.ensure_future(b.stop())
    done, _ = await asyncio.wait({task}, timeout=60)
    el = time.monotonic() - t0
    if not done:
        os.kill(pid, signal.SIGCONT)
        task.cancel()
    print(
        f"sigstop: done={bool(done)} elapsed={el:.1f}s exc={task.exception() if done else None!r} "
        f"alive={alive(pid)} profile={os.path.exists(udd)}",
        flush=True,
    )


async def kill_then_stop() -> None:
    b = await zd.start(headless=True)
    tab = await b.get("about:blank")
    await tab.evaluate("1")
    pid, udd = b._process_pid, b.config.user_data_dir
    assert b._process
    b._process.kill()
    try:
        await asyncio.wait_for(b.stop(), 30)
        exc = None
    except Exception as e:  # noqa
        exc = e
    print(
        f"kill_then_stop: exc={exc!r} _process={b._process} alive={alive(pid)} profile={os.path.exists(udd)}",
        flush=True,
    )


async def concurrent() -> None:
    b = await zd.start(headless=True)
    await b.get("about:blank")
    udd = b.config.user_data_dir
    first = asyncio.ensure_future(b.stop())
    await asyncio.sleep(float(os.environ.get("STAGGER", "0.1")))
    second = asyncio.ensure_future(b.stop())
    res = await asyncio.wait_for(asyncio.gather(first, second, return_exceptions=True), 30)
    print(f"concurrent: {res!r} profile={os.path.exists(udd)}", flush=True)


async def healthy() -> None:
    b = await zd.start(headless=True)
    for _ in range(3):
        await b.get("about:blank", new_tab=True)
    for t in b.tabs:
        await t.evaluate("1")
    t0 = time.monotonic()
    await b.stop()
    print(f"healthy: stop took {time.monotonic() - t0:.2f}s profile={os.path.exists(b.config.user_data_dir)}", flush=True)


state: dict[str, object] = {}


async def atexit_main() -> None:
    b = await zd.start(headless=True)
    tab = await b.get("about:blank")
    await tab.evaluate("1")
    state["udd"], state["pid"] = b.config.user_data_dir, b._process_pid


if __name__ == "__main__":
    mode = sys.argv[1]
    if mode == "atexit":
        asyncio.run(atexit_main())
        pid = state["pid"]
        assert isinstance(pid, int)
        print(f"atexit: alive={alive(pid)} profile={os.path.exists(str(state['udd']))}", flush=True)
    else:
        asyncio.run(globals()[mode]())
