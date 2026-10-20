import asyncio, time
import zendriver as zd
from zendriver import cdp

async def timed(label, coro):
    t = time.time()
    try:
        r = await coro
        print(f"{label}: OK in {time.time()-t:.2f}s -> {r}")
        return r
    except BaseException as e:
        print(f"{label}: {type(e).__name__} after {time.time()-t:.2f}s {e!r}"[:300])

async def main():
    cfg = zd.Config(headless=True)
    cfg.autodiscover_targets = False
    b = await zd.start(cfg)
    try:
        print("tabs:", b.tabs)
        await timed("get(data url) autodiscover off", b.get("data:text/html,<title>x</title>hi", timeout=3))
        t2 = await timed("get(new_tab) autodiscover off", b.get("data:text/html,two", new_tab=True, timeout=3))
        print("tabs:", b.tabs)
        if t2 is None:
            t2 = b.tabs[-1]
        await timed("close tab2", t2.close())
        await b.update_targets()
        print("tabs after close + update_targets:", b.tabs)
    finally:
        await b.stop()
asyncio.run(main())
