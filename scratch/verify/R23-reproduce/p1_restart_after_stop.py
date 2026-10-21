"""R23 / A3.2, B16.7, A12.4 part (1): stop() then start() on the same Browser."""
import asyncio
import os
import time
import traceback

import psutil
import zendriver as zd

print("zendriver from", zd.__file__)


def chrome_children():
    me = psutil.Process(os.getpid())
    return sorted(p.pid for p in me.children(recursive=False) if "chrom" in (p.name() or "").lower())


async def main():
    b = await zd.start(headless=True)
    first_pid = b._process_pid
    print("first start: pid", first_pid, "host/port", b.config.host, b.config.port,
          "ws", b.info.webSocketDebuggerUrl)
    print("chrome children after first start:", chrome_children())
    await b.stop()
    print("after stop: _process", b._process, "_process_pid", b._process_pid,
          "config host/port", b.config.host, b.config.port,
          "info stale:", b.info is not None, "targets kept:", len(b.targets),
          "connection closed:", b.connection.closed if b.connection else None)
    print("chrome children after stop:", chrome_children())

    t0 = time.monotonic()
    try:
        r = await asyncio.wait_for(b.start(), 60)
        print("restart returned", r, "same obj", r is b, "pid", b._process_pid)
    except Exception as e:
        print(f"restart raised after {time.monotonic() - t0:.2f}s: {type(e).__name__}: {e!r}"[:400])
        traceback.print_exc(limit=3)
    print("after restart attempt: _process", b._process, "_process_pid", b._process_pid,
          "chrome children:", chrome_children())
    try:
        await b.stop()
    except Exception as e:
        print("cleanup stop raised", repr(e))


asyncio.run(main())
