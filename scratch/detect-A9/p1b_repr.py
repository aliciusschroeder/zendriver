import asyncio, os, sys
import zendriver as zd

async def main(do_repr):
    cfg = zd.Config(headless=True)
    if do_repr:
        repr(cfg)
    b1 = await zd.start(cfg)
    d = b1.config.user_data_dir
    print("b1 udd:", d, "exists:", os.path.exists(d), "entries:", len(os.listdir(d)))
    try:
        b2 = await asyncio.wait_for(zd.start(cfg), 30)
        print("b2 ok, udd:", b2.config.user_data_dir)
        await b2.stop()
    except Exception as e:
        print("b2 start failed:", type(e).__name__)
    print("after b2 attempt: b1 profile exists:", os.path.exists(d))
    await b1.stop()

asyncio.run(asyncio.wait_for(main(sys.argv[1] == "1"), 90))
