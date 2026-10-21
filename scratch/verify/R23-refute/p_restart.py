"""Probe: does Browser.start() after stop() / after a crash relaunch Chrome?"""
import asyncio
import os
import sys
import time
import traceback

import psutil
import zendriver as zd

print("zendriver from", zd.__file__, "python", sys.version.split()[0])


def chrome_children():
    me = psutil.Process(os.getpid())
    return sorted(
        p.pid for p in me.children(recursive=False) if "chrom" in (p.name() or "")
    )


async def restart_after_stop():
    print("\n== restart after stop ==")
    b = await zd.start(headless=True)
    print("first start: pid", b._process_pid, "host/port", b.config.host, b.config.port)
    await b.get("data:text/html,<p>hi</p>")
    await b.stop()
    print(
        "after stop: host/port", b.config.host, b.config.port,
        "info stale:", b.info is not None, "targets kept:", len(b.targets),
        "connection closed:", b.connection.closed if b.connection else None,
        "chrome children:", chrome_children(),
    )
    t0 = time.monotonic()
    try:
        await asyncio.wait_for(b.start(), 60)
        print("restart OK after %.2fs, pid" % (time.monotonic() - t0), b._process_pid)
        try:
            tab = await asyncio.wait_for(b.get("data:text/html,<p>again</p>"), 30)
            print("get after restart OK", tab)
        except Exception as e:
            print("get after restart raised", type(e).__name__, e)
    except Exception as e:
        print("restart raised after %.2fs:" % (time.monotonic() - t0), type(e).__name__, repr(e)[:300])
    print("process launched by restart?", b._process_pid, "chrome children:", chrome_children())
    await b.stop()


async def restart_after_crash():
    print("\n== restart after crash ==")
    b = await zd.start(headless=True)
    pid = b._process_pid
    print("first start pid", pid, "port", b.config.port)
    b._process.kill()
    await asyncio.to_thread(b._process.wait)
    print("killed; stopped =", b.stopped)
    t0 = time.monotonic()
    nb = None
    try:
        nb = await asyncio.wait_for(b.start(), 60)
        print(
            "start after crash returned after %.2fs:" % (time.monotonic() - t0),
            "new instance?", nb is not b, "new pid", nb._process_pid, "port", nb.config.port,
        )
    except Exception as e:
        print("start after crash raised after %.2fs:" % (time.monotonic() - t0), type(e).__name__, repr(e)[:200].replace("\\n", " "))
    print("chrome children:", chrome_children())
    if nb is not None and nb is not b:
        await nb.stop()
    await b.stop()


async def main():
    await restart_after_stop()
    await restart_after_crash()
    print("\nleft chrome children:", chrome_children())


asyncio.run(main())
