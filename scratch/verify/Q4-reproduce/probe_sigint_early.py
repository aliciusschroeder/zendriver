"""Ctrl+C (SIGINT) 0.1s after Chrome is spawned, zendriver unpatched except a pid spy.
Usage: python probe_sigint_early.py <pidfile>"""
import asyncio, os, signal, sys, threading
import zendriver
from zendriver.core import util
print("zendriver from", zendriver.__file__, "python", sys.version.split()[0])
pidfile = sys.argv[1]
spawned = []
orig = util._start_process
def spy(*a, **kw):
    p = orig(*a, **kw); spawned.append(p)
    prof = next(x.split("=", 1)[1] for x in a[1] if x.startswith("--user-data-dir="))
    with open(pidfile, "a") as f:
        f.write(f"{p.pid} {prof}\n")
    threading.Timer(0.1, lambda: os.kill(os.getpid(), signal.SIGINT)).start()
    return p
util._start_process = spy
async def main():
    b = await zendriver.start(headless=True)
    print("start returned (unexpected)"); await b.stop()
try:
    asyncio.run(main())
except KeyboardInterrupt:
    print("KeyboardInterrupt from asyncio.run")
regs = list(util.get_registered_instances())
print("registered instances:", len(regs), [(r._process_pid, bool(r.info), r.config.user_data_dir) for r in regs])
for p in spawned:
    print("spawned pid", p.pid, "poll()", p.poll())
print("interpreter exiting")
