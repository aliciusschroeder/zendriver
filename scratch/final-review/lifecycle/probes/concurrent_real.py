import asyncio, os, sys, time, threading, gc, logging
import psutil, asyncio_atexit
import zendriver as zd
from zendriver.core import util

logging.basicConfig(level=logging.WARNING, format="LOG %(levelname)s %(name)s: %(message)s")
CHROME = os.popen("which chromium").read().strip()

def nfds():
    return len(os.listdir("/proc/self/fd"))

def atexit_callbacks():
    loop = asyncio.get_running_loop()
    e = asyncio_atexit._registry.get(loop)
    return len(e.callbacks) if e else 0

async def one_round(n):
    t0 = time.monotonic()
    browsers = await asyncio.gather(*(zd.start(headless=True, sandbox=False, browser_executable_path=CHROME) for _ in range(n)))
    t1 = time.monotonic()
    pids = []
    for b in browsers:
        p = psutil.Process(b._process_pid)
        pids += [b._process_pid] + [c.pid for c in p.children(recursive=True)]
    profiles = [b.config.user_data_dir for b in browsers]
    tails = [util._stderr_tails.get(b._process) for b in browsers]
    await asyncio.gather(*(b.get("data:text/html,<p>hi</p>") for b in browsers))
    print(f"  started {n} in {t1-t0:.2f}s; registry={len(util.get_registered_instances())} atexit={atexit_callbacks()} tails={len(util._stderr_tails)}")
    t2 = time.monotonic()
    res = await asyncio.gather(*(b.stop() for b in browsers), return_exceptions=True)
    t3 = time.monotonic()
    await asyncio.sleep(0.3)
    alive = [pid for pid in pids if psutil.pid_exists(pid) and psutil.Process(pid).status() != psutil.STATUS_ZOMBIE]
    print(f"  stop results={res} took {t3-t2:.2f}s alive={alive} profiles_left={[p for p in profiles if os.path.exists(p)]}")
    print(f"  threads alive={[t._thread.is_alive() for t in tails]} registry={len(util.get_registered_instances())} atexit={atexit_callbacks()}")
    del browsers, tails
    gc.collect()
    print(f"  tails after gc={len(util._stderr_tails)} fds={nfds()} threads={[t.name for t in threading.enumerate()]}")

async def main():
    print("fds at start", nfds())
    for r in range(3):
        print("round", r)
        await one_round(3)
    print("fds at end", nfds())

asyncio.run(main())
