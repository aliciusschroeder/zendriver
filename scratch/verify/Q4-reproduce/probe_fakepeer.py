"""Q4 reproducer with NO monkeypatching of zendriver internals other than a pid spy:
a fake browser executable whose CDP endpoint rejects Target.setDiscoverTargets.
Usage: python probe_fakepeer.py <pidfile>"""
import asyncio, os, sys
import zendriver
from zendriver.core import util

print("zendriver from", zendriver.__file__, "python", sys.version.split()[0])
pidfile = sys.argv[1]
FAKE = "/tmp/claude-0/-home-user-zendriver/b2021b39-94e6-5220-9e66-7f33c0314a80/scratchpad/verify/Q4-reproduce/fakebin/fake-chrome"
spawned = []
orig = util._start_process
def spy(*a, **kw):
    p = orig(*a, **kw); spawned.append(p)
    prof = next(x.split("=", 1)[1] for x in a[1] if x.startswith("--user-data-dir="))
    with open(pidfile, "a") as f:
        f.write(f"{p.pid} {prof}\n")
    return p
util._start_process = spy

async def main():
    try:
        b = await asyncio.wait_for(zendriver.start(headless=True, browser_executable_path=FAKE), 30)
        print("start returned (unexpected)"); await b.stop()
    except Exception as e:
        print(f"start raised {type(e).__name__}: {e}")
    regs = list(util.get_registered_instances())
    print("registered instances:", len(regs))
    for r in regs:
        print("  pid", r._process_pid, "connection", r.connection, "profile", r.config.user_data_dir,
              "exists", os.path.isdir(r.config.user_data_dir))
    for p in spawned:
        print("spawned pid", p.pid, "poll()", p.poll())

asyncio.run(main())
print("interpreter exiting")
