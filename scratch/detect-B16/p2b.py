import asyncio, os, glob, tempfile, subprocess, time
import zendriver as zd
from zendriver.core import util

async def main():
    t=time.time()
    b = await zd.start(headless=True)
    print("start took", time.time()-t, b._process_pid, b.stopped)
    await b.stop()
    for delay in (0.15, 0.6):
        try:
            await asyncio.wait_for(zd.start(headless=True), delay)
        except asyncio.TimeoutError:
            print("timed out after", delay)
        await asyncio.sleep(1.0)
        for b in util.get_registered_instances():
            p = b._process
            print(" pid", b._process_pid, "poll", p.poll() if p else None)
            if p and p.poll() is not None:
                print("  stderr:", p.stderr.read(3000)[:1500])
asyncio.run(main())
