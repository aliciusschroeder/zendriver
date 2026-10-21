"""cancel zd.start() at increasing delays (asyncio.timeout on 3.11+, wait_for on 3.10)
and check: TimeoutError raised, chrome process gone, profile removed, no asyncio noise."""
import asyncio, logging, os, sys, time, glob
import zendriver as zd
import zendriver.core.util as zutil

logging.basicConfig(level=logging.WARNING, format="%(levelname)s %(name)s: %(message)s")
started = []
orig = zutil._start_process
def track(*a, **k):
    p = orig(*a, **k)
    started.append(p)
    return p
zutil._start_process = track


async def one(delay: float) -> str:
    started.clear()
    before = set(glob.glob("/tmp/uc_*"))
    t0 = time.monotonic()
    outcome = "returned"
    browser = None
    try:
        if sys.version_info >= (3, 11):
            async with asyncio.timeout(delay):
                browser = await zd.start(headless=True, sandbox=False, browser_executable_path=os.environ["CHROME"])
        else:
            browser = await asyncio.wait_for(zd.start(headless=True, sandbox=False, browser_executable_path=os.environ["CHROME"]), delay)
    except BaseException as e:
        outcome = type(e).__name__
    dt = time.monotonic() - t0
    if browser is not None:
        await browser.stop()
    p = started[0] if started else None
    rc = p.poll() if p else "no-process"
    if p and rc is None:
        p.kill(); p.wait()
        rc = "STILL RUNNING (killed by probe)"
    leftover = set(glob.glob("/tmp/uc_*")) - before
    return f"delay={delay:.2f} outcome={outcome} after {dt:.2f}s rc={rc} new_profiles_left={len(leftover)}"


async def main():
    print("python", sys.version.split()[0], zd.__file__, flush=True)
    import os as _os
    lo, hi, step = (float(x) for x in _os.environ.get("SCAN", "0.1,1.2,0.1").split(","))
    d = lo
    while d <= hi + 1e-9:
        print(" ", await one(d), flush=True)
        d += step
    print("tasks left:", [t for t in asyncio.all_tasks() if t is not asyncio.current_task()], flush=True)

asyncio.run(main())
print("exited cleanly")
