import asyncio, os, shutil, sys
import zendriver as zd
print("zendriver from", zd.__file__)

async def main():
    b = await zd.start(headless=True)
    await b.get("about:blank")
    udd = b.config.user_data_dir
    pid = b._process.pid
    res = await asyncio.wait_for(asyncio.gather(b.stop(), b.stop(), return_exceptions=True), 60)
    print("results:", [repr(r) for r in res], "profile exists:", os.path.exists(udd))
    try:
        os.kill(pid, 9)
    except ProcessLookupError:
        pass
    shutil.rmtree(udd, ignore_errors=True)

asyncio.run(main())
