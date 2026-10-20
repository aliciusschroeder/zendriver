import asyncio, os
import zendriver as zd

async def main():
    config = zd.Config(headless=True, browser_connection_max_tries=40)
    import sys
    if sys.argv[1:] == ["repr"]: repr(config)
    b1 = await asyncio.wait_for(zd.start(config), 30)
    print("b1 udd", b1.config.user_data_dir, "custom?", b1.config.uses_custom_data_dir)
    try:
        b2 = await asyncio.wait_for(zd.start(config), 60)
        print("b2 udd", b2.config.user_data_dir, "pid", b2._process_pid, "poll", b2._process.poll())
    except Exception as e:
        print("b2 start failed:", type(e).__name__, " ".join(str(e).split())[:120])
        b2 = None
    await asyncio.wait_for(b1.stop(), 30)
    print("after b1.stop, profile exists?", os.path.exists(config.user_data_dir))
    if b2:
        await asyncio.wait_for(b2.stop(), 30)

asyncio.run(main())
