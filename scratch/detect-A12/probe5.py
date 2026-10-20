import asyncio, sys, time
import zendriver as zd
from zendriver import cdp
sys.path.insert(0, "/home/user/zendriver")
from tests.sample_data import sample_file

async def main():
    config = zd.Config(headless=True)
    config.autodiscover_targets = False
    browser = await zd.start(config)
    try:
        t0 = time.monotonic()
        try:
            tab = await browser.get(sample_file("groceries.html"), timeout=4)
            print("get ok in %.1fs" % (time.monotonic()-t0), await tab.evaluate("document.title"))
        except Exception as e:
            print("get raised %s after %.1fs" % (type(e).__name__, time.monotonic()-t0))
            print("but page title:", await browser.tabs[0].evaluate("document.title"))
        t0 = time.monotonic()
        try:
            t2 = await browser.get("about:blank", new_tab=True, timeout=4)
            print("new_tab ok in %.1fs" % (time.monotonic()-t0))
        except Exception as e:
            print("new_tab raised %s after %.1fs" % (type(e).__name__, time.monotonic()-t0))
        t0 = time.monotonic()
        try:
            await browser.tabs[-1].close()
            print("close ok in %.1fs" % (time.monotonic()-t0))
        except Exception as e:
            print("close raised %s after %.1fs" % (type(e).__name__, time.monotonic()-t0))
    finally:
        await browser.stop()

asyncio.run(asyncio.wait_for(main(), 55))
