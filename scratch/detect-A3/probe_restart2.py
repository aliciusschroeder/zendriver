import asyncio, shutil
import zendriver as zd

async def main():
    b = await zd.start(headless=True)
    old_ids = [t.target_id for t in b.tabs]
    await b.stop()
    b.config.host = b.config.port = None   # work around the first defect to look past it
    await asyncio.wait_for(b.start(), 30)
    print("after restart: tabs", [(t.target_id in old_ids) for t in b.tabs], "first tab is stale:", b.tabs[0].target_id in old_ids)
    try:
        await asyncio.wait_for(b.get("about:blank"), 15)
        print("get ok")
    except Exception as e:
        print("get after restart raised", type(e).__name__, str(e)[:120])
    await b.stop()
    shutil.rmtree(b.config.user_data_dir, ignore_errors=True)

asyncio.run(main())
