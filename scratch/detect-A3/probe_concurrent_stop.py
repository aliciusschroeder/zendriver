import asyncio, shutil
import zendriver as zd

async def main():
    b = await zd.start(headless=True)
    udd = b.config.user_data_dir; proc = b._process
    await b.get("about:blank")
    res = await asyncio.wait_for(asyncio.gather(b.stop(), b.stop(), return_exceptions=True), 30)
    print("results:", [repr(r) for r in res])
    print("process exited:", proc.poll())
    if proc.poll() is None: proc.kill(); proc.wait()
    shutil.rmtree(udd, ignore_errors=True)

asyncio.run(main())
