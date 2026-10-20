import asyncio, os, shutil, sys
import zendriver as zd
print("zendriver from", zd.__file__)

async def one(offset):
    b = await zd.start(headless=True)
    await b.get("about:blank")
    udd = b.config.user_data_dir
    pid = b._process.pid
    a = asyncio.ensure_future(b.stop())
    await asyncio.sleep(offset)
    c = asyncio.ensure_future(b.stop())
    res = await asyncio.wait_for(asyncio.gather(a, c, return_exceptions=True), 60)
    try:
        os.kill(pid, 9)
    except ProcessLookupError:
        pass
    leaked = os.path.exists(udd)
    shutil.rmtree(udd, ignore_errors=True)
    return [type(r).__name__ for r in res], leaked

async def main():
    for offset in (0.05, 0.1, 0.15, 0.2):
        for _ in range(3):
            print(offset, *(await one(offset)))

asyncio.run(main())
