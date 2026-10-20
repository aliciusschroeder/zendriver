import asyncio, sys, logging
import zendriver as zd
from zendriver import cdp
sys.path.insert(0, "/home/user/zendriver")
from tests.sample_data import sample_file
logging.basicConfig(level=logging.ERROR)

async def main():
    browser = await zd.start(headless=True)
    try:
        tab = await browser.get("about:blank")
        seen = []
        def on_paused(ev: cdp.fetch.RequestPaused, conn):
            seen.append(ev.request.url)
            conn.feed_cdp(cdp.fetch.continue_request(request_id=ev.request_id))
        tab.add_handler(cdp.fetch.RequestPaused, on_paused)
        try:
            await tab.get(sample_file("groceries.html"), timeout=5)
            await tab.wait_for_ready_state("complete", timeout=5)
            print("nav ok; handler saw", seen)
        except Exception as e:
            print("nav raised", type(e).__name__, e, "handler saw", seen)
    finally:
        await browser.stop()

asyncio.run(asyncio.wait_for(main(), 50))
