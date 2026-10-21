"""R23 / A3.2, B16.7, A12.4 part (2): Chrome dies on its own, then start()."""
import asyncio
import os
import time

import psutil
import zendriver as zd
from zendriver.core import util

print("zendriver from", zd.__file__)


def chrome_children():
    me = psutil.Process(os.getpid())
    return sorted(p.pid for p in me.children(recursive=False) if "chrom" in (p.name() or "").lower())


async def main():
    b = await zd.start(headless=True)
    print("first start: pid", b._process_pid, "host/port", b.config.host, b.config.port)
    # simulate a crash / user closing chrome
    b._process.kill()
    b._process.wait()
    print("killed; poll()", b._process.poll(), "stopped", b.stopped, "children", chrome_children())

    # spy on _start_process to see if a new Chrome gets launched
    launched = []
    orig = util._start_process

    def spy(*a, **k):
        p = orig(*a, **k)
        launched.append(p.pid)
        return p

    util._start_process = spy
    t0 = time.monotonic()
    try:
        r = await asyncio.wait_for(b.start(), 60)
        print("start after crash returned", r, "same obj", r is b, "new pid", r._process_pid)
        await r.stop()
    except Exception as e:
        msg = " ".join(str(e).split())
        print(f"start after crash raised after {time.monotonic() - t0:.2f}s: {type(e).__name__}: {msg[:200]}")
    print("processes launched by restart:", launched, "children now:", chrome_children())
    util._start_process = orig
    # cleanup the old instance (its process is dead)
    try:
        await b.stop()
    except Exception as e:
        print("cleanup stop raised", repr(e))


asyncio.run(main())
