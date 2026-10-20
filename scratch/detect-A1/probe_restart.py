import asyncio
import zendriver as zd

async def main():
    browser = await zd.start(headless=True)
    tab = await browser.get("about:blank")
    await tab.evaluate("1")
    old_ids = [t.target_id for t in browser.targets]
    await browser.stop()
    print("targets after stop:", len(browser.targets))
    await browser.start()
    try:
        print("targets after restart:", len(browser.targets), "stale:", sum(t.target_id in old_ids for t in browser.targets))
        print("tabs[0] is stale:", browser.tabs[0].target_id in old_ids)
        try:
            t = await asyncio.wait_for(browser.get("data:text/html,<p>hi</p>"), 20)
            print("get ok:", t.target_id in old_ids)
        except Exception as e:
            print("browser.get after restart raised", type(e).__name__, str(e).splitlines()[0])
    finally:
        await browser.stop()

asyncio.run(main())
