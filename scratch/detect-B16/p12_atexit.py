import asyncio, json
import zendriver as zd

info = {}
async def main():
    b = await zd.start(headless=True)
    await b.get("about:blank")
    info["pid"] = b._process_pid
    info["dir"] = b.config.user_data_dir
    # no explicit stop(): rely on the documented atexit cleanup

asyncio.run(main())
json.dump(info, open("atexit.json", "w"))
