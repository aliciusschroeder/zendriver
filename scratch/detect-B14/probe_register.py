import asyncio, traceback
import zendriver as zd
from zendriver import cdp

async def main():
    browser = await zd.start(headless=True)
    try:
        tab = await browser.get("about:blank")
        async def h1(e): pass
        async def h2(e): pass
        tab.add_handler(cdp.network.RequestWillBeSent, h1)
        await tab.evaluate("1")   # network auto-enabled
        print("enabled_domains after first send:", [d.__name__ for d in tab.enabled_domains])
        # switch listening from network to runtime console events
        tab.remove_handlers(cdp.network.RequestWillBeSent, h1)
        tab.add_handler(cdp.runtime.ConsoleAPICalled, h2)
        try:
            r = await tab.evaluate("2")
            print("second evaluate OK:", r)
        except Exception as e:
            print("second evaluate RAISED:", type(e).__name__, e)
            traceback.print_exc()
        print("enabled_domains now:", [d.__name__ for d in tab.enabled_domains])
        print("third evaluate:", await tab.evaluate("3"))
    finally:
        await browser.stop()

asyncio.run(asyncio.wait_for(main(), 50))
