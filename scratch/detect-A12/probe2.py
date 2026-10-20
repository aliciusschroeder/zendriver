import asyncio, sys
import zendriver as zd
from zendriver import cdp
sys.path.insert(0, "/home/user/zendriver")
from tests.sample_data import sample_file

async def main():
    browser = await zd.start(headless=True)
    try:
        tab = await browser.get("about:blank")
        paused = []
        async def on_paused(ev: cdp.fetch.RequestPaused, conn):
            paused.append(ev.request.url)
            await conn.send(cdp.fetch.continue_request(request_id=ev.request_id))
        tab.add_handler(cdp.fetch.RequestPaused, on_paused)
        await tab.get(sample_file("groceries.html"))
        await tab.wait_for_ready_state("complete")
        print("with handler: paused", len(paused), "enabled", tab.enabled_domains)
        tab.remove_handlers(cdp.fetch.RequestPaused, on_paused)
        print("after remove: handlers", dict(tab.handlers))
        n = len(paused)
        try:
            await tab.get(sample_file("profile.html"), timeout=5)
            await tab.wait_for_ready_state("complete", timeout=5)
            print("second nav ok; url", await tab.evaluate("location.href"))
        except Exception as e:
            print("second nav raised", type(e).__name__, e)
        print("enabled_domains", tab.enabled_domains, "manual", tab.manually_enabled_domains)
        # is Fetch still enabled browser side? try continue... check readyState
        try:
            rs = await asyncio.wait_for(tab.evaluate("document.readyState + ' ' + location.href"), 5)
            print("state", rs)
        except Exception as e:
            print("evaluate raised", type(e).__name__, e)
    finally:
        await browser.stop()

asyncio.run(asyncio.wait_for(main(), 50))
