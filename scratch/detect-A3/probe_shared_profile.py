import asyncio, os, shutil
import zendriver as zd

async def main():
    config = zd.Config(headless=True)
    print("template repr touches user_data_dir:", "user_data_dir" in repr(config))
    b1 = await zd.start(config)
    print("b1 udd", b1.config.user_data_dir)
    try:
        b2 = await asyncio.wait_for(zd.start(config), 20)
        print("b2 udd", b2.config.user_data_dir, "same:", b1.config.user_data_dir == b2.config.user_data_dir)
        print("b2 pid", b2._process_pid, "alive", not b2.stopped)
        await b1.stop()
        print("after b1.stop(): b2 still running:", not b2.stopped, "b2 profile dir exists:", os.path.exists(b2.config.user_data_dir))
        await b2.stop()
    except Exception as e:
        print("b2 failed:", type(e).__name__, str(e).strip().splitlines()[:2]); print("b1 still running:", not b1.stopped, "b1 profile dir exists:", os.path.exists(b1.config.user_data_dir))
        await b1.stop()
    shutil.rmtree(b1.config.user_data_dir, ignore_errors=True)

asyncio.run(main())
