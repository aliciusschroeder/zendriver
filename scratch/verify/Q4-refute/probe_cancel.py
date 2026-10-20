"""Q4 refute probe: does cancelling zd.start() after spawn leak Chrome/profile/registry?"""
import asyncio, json, os, sys, time, pathlib
import psutil
import zendriver as zd
from zendriver.core import util

OUT = pathlib.Path(sys.argv[1])
TIMEOUTS = [float(x) for x in sys.argv[2:]] or [0.05, 0.3]
spawned = []  # (pid, user_data_dir)

orig = util._start_process
def spy(exe, params, is_posix, env=None):
    p = orig(exe, params, is_posix, env=env)
    udd = next((a.split("=", 1)[1] for a in params if a.startswith("--user-data-dir=")), None)
    spawned.append({"pid": p.pid, "udd": udd})
    OUT.write_text(json.dumps(spawned))
    return p
util._start_process = spy

def alive(pid):
    try:
        pr = psutil.Process(pid)
        return pr.status() != psutil.STATUS_ZOMBIE
    except psutil.NoSuchProcess:
        return False

async def main():
    print("zendriver from", zd.__file__, "python", sys.version.split()[0])
    # baseline: how long does an uncancelled start take here?
    t0 = time.perf_counter()
    b = await zd.start(headless=True)
    print(f"baseline start took {time.perf_counter()-t0:.3f}s")
    await b.stop()
    print("baseline after stop: alive", alive(spawned[-1]["pid"]), "profile exists", os.path.exists(spawned[-1]["udd"]),
          "registered", len(util.get_registered_instances()))
    for T in TIMEOUTS:
        n = len(spawned)
        t0 = time.perf_counter()
        try:
            b = await asyncio.wait_for(zd.start(headless=True), T)
            print(f"T={T}: start finished in {time.perf_counter()-t0:.3f}s (not cancelled)")
            await b.stop()
        except asyncio.TimeoutError:
            print(f"T={T}: timed out after {time.perf_counter()-t0:.3f}s")
        if len(spawned) > n:
            s = spawned[-1]
            await asyncio.sleep(1.0)
            regs = [r for r in util.get_registered_instances() if r._process_pid == s["pid"]]
            print(f"   pid {s['pid']} alive={alive(s['pid'])} profile_exists={os.path.exists(s['udd'])} "
                  f"in_registry={bool(regs)} conn={regs[0].connection if regs else None}")
        else:
            print("   cancelled before spawn")

asyncio.run(main())
print("after asyncio.run:", [(s["pid"], alive(s["pid"]), os.path.exists(s["udd"])) for s in spawned])
