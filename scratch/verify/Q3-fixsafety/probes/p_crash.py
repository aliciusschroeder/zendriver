import asyncio, os, signal, shutil, sys
import zendriver as zd
print("zendriver from", zd.__file__)

async def main():
    b = await zd.start(headless=True)
    tab = await b.get("about:blank")
    await tab.evaluate("1")
    pid = b._process.pid
    udd = b.config.user_data_dir
    b._process.kill()
    try:
        await asyncio.wait_for(b.stop(), 30)
        print("stop OK")
    except BaseException as e:
        print("stop RAISED", type(e).__name__, e)
    print("_process still set:", b._process is not None, "profile exists:", os.path.exists(udd))
    if b._process: b._process.wait()
    shutil.rmtree(udd, ignore_errors=True)

asyncio.run(main())
