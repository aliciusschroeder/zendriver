import asyncio, os
import zendriver as zd
holder = {}
async def main():
    b = await zd.start(headless=True)
    await b.get("about:blank")
    holder["udd"] = b.config.user_data_dir
    holder["pid"] = b._process_pid
    # no explicit stop: rely on the asyncio_atexit cleanup that Browser.create registers
asyncio.run(main())
import psutil
print("profile dir still exists after asyncio.run():", os.path.exists(holder["udd"]), holder["udd"])
print("browser pid alive:", psutil.pid_exists(holder["pid"]) and psutil.Process(holder["pid"]).status())
