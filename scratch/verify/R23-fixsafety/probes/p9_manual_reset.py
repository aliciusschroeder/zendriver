import asyncio, sys
import asyncio_atexit
import zendriver as zd
print("zendriver from", zd.__file__)
async def main():
    b = await zd.start(headless=True)
    await b.get("about:blank")
    await b.stop()
    b.config.host = None; b.config.port = None  # reset by hand
    await asyncio.wait_for(b.start(), 60)
    cbs = asyncio_atexit._get_entry().callbacks
    print("restarted; targets:", len(b.targets), "atexit registered:", b._atexit_cleanup in cbs)
    try:
        await asyncio.wait_for(b.get("about:blank"), 20)
        print("get OK")
    except Exception as e:
        print("get after restart raised", type(e).__name__, str(e).splitlines()[0], "| tabs[0] stale:", b.tabs[0].target_id not in [t.target_id for t in await b._get_targets()])
    finally:
        await b.stop()
asyncio.run(main())
