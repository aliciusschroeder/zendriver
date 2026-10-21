import asyncio, sys, psutil, os
import zendriver as zd
print("zendriver from", zd.__file__, sys.version.split()[0])
pids = []
async def main():
    for i in range(3):
        async with await zd.start(headless=True) as b:
            await b.main_tab.evaluate("1")
        pids.append(b._process_pid)
        print(f"after async with #{i}: stopped={b.stopped} pid={b._process_pid} alive={psutil.pid_exists(b._process_pid)}")
    print("chrome procs alive inside loop:", [p for p in pids if psutil.pid_exists(p) and psutil.Process(p).status() != psutil.STATUS_ZOMBIE])
    # exception inside the block: does it propagate unchanged?
    class MyErr(Exception):
        def __init__(self, a, b): super().__init__(a, b)
    try:
        async with await zd.start(headless=True) as b2:
            pids.append(b2._process_pid)
            raise MyErr("x", "y")
    except Exception as e:
        print("exception from block:", type(e).__name__, e)
asyncio.run(main())
import time; time.sleep(1)
print("after asyncio.run (atexit cleanup ran):", [(p, psutil.pid_exists(p) and psutil.Process(p).status()) for p in pids])
for p in pids:
    try: os.kill(p, 9)
    except ProcessLookupError: pass
