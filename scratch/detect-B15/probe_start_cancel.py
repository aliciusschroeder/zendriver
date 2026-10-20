import asyncio, os, subprocess, zendriver as zd
from zendriver.core import util

leaked = []
orig = util._start_process
def spy(exe, params, is_posix, env=None):
    p = orig(exe, params, is_posix, env)
    leaked.append(p)
    return p
util._start_process = spy

async def main():
    for delay in (0.05, 0.3, 0.6):
        try:
            b = await asyncio.wait_for(zd.start(headless=True), delay)
            print(delay, "started fully, stopping"); await b.stop()
        except asyncio.TimeoutError:
            print(delay, "timed out")
    await asyncio.sleep(1)
    for p in leaked:
        print("pid", p.pid, "still running:", p.poll() is None)

asyncio.run(main())
# after event loop has finished (atexit cleanup would have run here if registered)
import time; time.sleep(1)
alive = [p for p in leaked if p.poll() is None]
print("alive after asyncio.run returned:", [p.pid for p in alive])
for p in leaked:
    args = p.args
    udd = [a for a in args if a.startswith("--user-data-dir=")]
    print("profile dir exists:", udd and os.path.exists(udd[0].split("=",1)[1]))
for p in alive:
    p.kill(); p.wait()
