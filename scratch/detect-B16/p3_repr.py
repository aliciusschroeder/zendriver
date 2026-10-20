import asyncio, os
import zendriver as zd

async def main():
    config = zd.Config(headless=True, browser_connection_max_tries=8)
    print("template before repr:", config._user_data_dir)
    repr(config)  # e.g. print(config) / logging the config
    print("template after repr:", config._user_data_dir, "custom?", config.uses_custom_data_dir)
    b1 = await zd.start(config)
    print("b1 dir", b1.config.user_data_dir)
    try:
        b2 = await zd.start(config)
        print("b2 dir", b2.config.user_data_dir, "same?", b2.config.user_data_dir == b1.config.user_data_dir)
        await b2.stop()
    except Exception as e:
        print("b2 start failed:", type(e).__name__, str(e).strip().splitlines()[1].strip())
    print("b1 profile dir still exists?", os.path.isdir(b1.config.user_data_dir))
    t = await b1.get("about:blank")
    print("b1 still works:", await t.evaluate("1+1"))
    await b1.stop()

asyncio.run(asyncio.wait_for(main(), 50))
