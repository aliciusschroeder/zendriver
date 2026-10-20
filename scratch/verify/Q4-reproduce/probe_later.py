"""Q4 reproducer: start() fails or is cancelled AFTER the CDP connection is up.

Usage: python probe_later.py <mode> <pidfile>
modes:
  raise_ua      - _read_headless_user_agent raises (stands in for a CDP error there)
  raise_update  - update_targets raises ProtocolException (first call, right after set_discover_targets)
  cancel_ua     - _read_headless_user_agent stalls; wait_for(start, 3) cancels it there
  sigint        - SIGINT (Ctrl+C) arrives while _read_headless_user_agent stalls
"""
import asyncio
import os
import signal
import sys
import threading
import time

import zendriver
from zendriver.core import util
from zendriver.core.browser import Browser
from zendriver.core.connection import ProtocolException

print("zendriver from", zendriver.__file__, "python", sys.version.split()[0])
mode, pidfile = sys.argv[1], sys.argv[2]
spawned = []
orig = util._start_process


def spy(*a, **kw):
    p = orig(*a, **kw)
    spawned.append(p)
    prof = next(x.split("=", 1)[1] for x in a[1] if x.startswith("--user-data-dir="))
    with open(pidfile, "a") as f:
        f.write(f"{p.pid} {prof}\n")
    return p


util._start_process = spy

orig_ua = Browser._read_headless_user_agent
orig_update = Browser.update_targets
reached = {}


async def ua_raise(self):
    reached["ua"] = (self.connection is not None, self.connection and not self.connection.closed)
    raise RuntimeError("simulated failure inside _read_headless_user_agent")


async def ua_stall(self):
    reached["ua"] = (self.connection is not None, self.connection and not self.connection.closed)
    if mode == "sigint":
        threading.Timer(0.3, lambda: os.kill(os.getpid(), signal.SIGINT)).start()
    await asyncio.sleep(60)


async def update_raise(self):
    reached["update"] = (self.connection is not None,)
    raise ProtocolException({"code": -32000, "message": "simulated Target.getTargets failure"})


if mode == "raise_ua":
    Browser._read_headless_user_agent = ua_raise
elif mode in ("cancel_ua", "sigint"):
    Browser._read_headless_user_agent = ua_stall
elif mode == "raise_update":
    Browser.update_targets = update_raise


def report(tag):
    regs = list(util.get_registered_instances())
    print(f"[{tag}] registered instances: {len(regs)}")
    for r in regs:
        c = r.connection
        print(
            f"[{tag}]   pid {r._process_pid} info set {bool(r.info)} "
            f"connection {'None' if c is None else ('closed' if c.closed else 'OPEN')} "
            f"profile {r.config.user_data_dir} exists {os.path.isdir(r.config.user_data_dir)}"
        )
    for p in spawned:
        print(f"[{tag}] spawned pid {p.pid} poll() {p.poll()}")


async def main():
    t0 = time.monotonic()
    try:
        if mode == "cancel_ua":
            b = await asyncio.wait_for(zendriver.start(headless=True), 3)
        else:
            b = await asyncio.wait_for(zendriver.start(headless=True), 30)
        print("start returned (unexpected)")
        await b.stop()
    except BaseException as e:
        print(f"start raised {type(e).__name__}: {e} after {time.monotonic()-t0:.2f}s; reached={reached}")
        report("in loop")
        if isinstance(e, (KeyboardInterrupt, asyncio.CancelledError)):
            raise


try:
    asyncio.run(main())
except KeyboardInterrupt:
    print("asyncio.run raised KeyboardInterrupt (Ctrl+C path)")
report("after asyncio.run")
print("interpreter exiting")
