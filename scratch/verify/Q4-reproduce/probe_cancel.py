"""Q4 reproducer: cancel zd.start() after Chrome was spawned.

Usage: python probe_cancel.py <timeout_seconds> <pidfile>
Writes the spawned pid and profile dir to <pidfile> so the parent can check
after this interpreter exits.
"""
import asyncio
import os
import sys
import time

import zendriver
from zendriver.core import util

print("zendriver from", zendriver.__file__, "python", sys.version.split()[0])

timeout = float(sys.argv[1])
pidfile = sys.argv[2]
spawned = []

orig = util._start_process


def spy(*a, **kw):
    p = orig(*a, **kw)
    spawned.append(p)
    prof = next(x.split("=", 1)[1] for x in a[1] if x.startswith("--user-data-dir="))
    with open(pidfile, "a") as f:
        f.write(f"{p.pid} {prof}\n")
    return p


util._start_process = spy  # browser.py calls util._start_process via the module


async def main():
    t0 = time.monotonic()
    try:
        b = await asyncio.wait_for(zendriver.start(headless=True), timeout)
        print(f"start completed in {time.monotonic()-t0:.3f}s (no cancel); stopping")
        await b.stop()
    except (asyncio.TimeoutError, TimeoutError):
        print(f"start timed out after {time.monotonic()-t0:.3f}s")
    regs = list(util.get_registered_instances())
    print("registered instances:", len(regs))
    for r in regs:
        print(
            "  registered: pid", r._process_pid,
            "info set", bool(r.info), "connection", r.connection,
            "profile", r.config.user_data_dir,
            "exists", os.path.isdir(r.config.user_data_dir),
        )
    for p in spawned:
        print("spawned pid", p.pid, "poll()", p.poll())


asyncio.run(main())
for p in spawned:
    print("after asyncio.run: pid", p.pid, "poll()", p.poll())
print("interpreter exiting")
