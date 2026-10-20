import asyncio, os, shutil
import zendriver as zd
print("zendriver from", zd.__file__)
async def main():
    b = await zd.start(headless=True)
    t = await b.get("about:blank")
    await t.evaluate("1")
    udd = b.config.user_data_dir
    loop = asyncio.get_running_loop(); t0 = loop.time()
    await asyncio.wait_for(b.stop(), 30)
    print("normal stop took %.2fs, profile exists: %s" % (loop.time() - t0, os.path.exists(udd)))
asyncio.run(main())
