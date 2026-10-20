import asyncio, os, logging
import zendriver as zd

async def main():
    cfg = zd.Config(headless=True)
    print("template _user_data_dir before repr:", cfg._user_data_dir)
    r = repr(cfg)
    print("template _user_data_dir after repr:", cfg._user_data_dir)
    b1 = await zd.start(cfg)
    try:
        b2 = await asyncio.wait_for(zd.start(cfg), 30)
    except Exception as e:
        print("b2 start failed:", type(e).__name__, str(e).strip()[:120])
        b2 = None
    print("b1 udd:", b1.config.user_data_dir)
    if b2: print("b2 udd:", b2.config.user_data_dir)
    if b2:
        print("same:", b1.config.user_data_dir == b2.config.user_data_dir)
        print("b1 pid", b1._process_pid, "b2 pid", b2._process_pid, "b2 poll", b2._process.poll())
        await b1.stop()
        print("after b1.stop, dir exists:", os.path.exists(b2.config.user_data_dir))
        try:
            t = await asyncio.wait_for(b2.get("about:blank"), 15)
            print("b2 still usable", t)
        except Exception as e:
            print("b2 get failed", type(e).__name__, e)
        await b2.stop()
    else:
        await b1.stop()

asyncio.run(asyncio.wait_for(main(), 90))
