import asyncio, time, shutil
import zendriver as zd

async def main():
    b = await zd.start(headless=True)
    udd = b.config.user_data_dir
    b._process.kill(); b._process.wait()
    print("stopped:", b.stopped)
    t0 = time.monotonic()
    try:
        r = await asyncio.wait_for(b.start(), 30)
        print("start returned", r is b, r._process)
    except Exception as e:
        print("start after crash raised after %.2fs:" % (time.monotonic()-t0), type(e).__name__, str(e).strip().splitlines()[:3])
    await b.stop()
    shutil.rmtree(udd, ignore_errors=True)

asyncio.run(main())
