import asyncio, os, sys, threading, time, gc
import psutil
import zendriver
from zendriver.core import util

def stderr_threads():
    return [t for t in threading.enumerate() if t.name == "zendriver-browser-stderr"]

async def main():
    print("zendriver from", zendriver.__file__)
    for i in range(3):
        b = await zendriver.start(headless=True)
        p = b._process
        pid = p.pid
        # find the pipe inode of chrome's fd 2
        target = os.readlink(f"/proc/{pid}/fd/2")
        holders = []
        for proc in psutil.process_iter(["pid", "name"]):
            try:
                if os.readlink(f"/proc/{proc.pid}/fd/2") == target:
                    holders.append((proc.pid, proc.info["name"]))
            except Exception:
                pass
        print("run", i, "chrome", pid, "stderr", target, "holders", len(holders), sorted(set(n for _, n in holders)))
        await b.stop()
        del b, p
        gc.collect()
        await asyncio.sleep(2)
        left = []
        for proc in psutil.process_iter(["pid", "name"]):
            try:
                if os.readlink(f"/proc/{proc.pid}/fd/2") == target:
                    left.append((proc.pid, proc.info["name"], proc.ppid()))
            except Exception:
                pass
        print("  after stop: drain threads alive", len(stderr_threads()), "procs still holding write end", left, "tails", len(util._stderr_tails) if hasattr(util, "_stderr_tails") else "n/a")

asyncio.run(main())
