import asyncio, traceback
import zendriver as zd
from zendriver import cdp

async def main():
    browser = await zd.start(headless=True)
    try:
        tab = await browser.get("about:blank")
        print("initial enabled", tab.enabled_domains, tab.manually_enabled_domains)
        async def on_req(e): pass
        async def on_console(e): pass
        tab.add_handler(cdp.network.RequestWillBeSent, on_req)
        await tab.send(cdp.runtime.evaluate("1"))
        print("after 1st send enabled", [m.__name__ for m in tab.enabled_domains])
        tab.remove_handlers(cdp.network.RequestWillBeSent, on_req)
        tab.add_handler(cdp.log.EntryAdded, on_console)
        try:
            r = await asyncio.wait_for(tab.send(cdp.runtime.evaluate("1+1")), 10)
            print("2nd send ok", r)
        except Exception as e:
            print("2nd send raised:", type(e).__name__, e)
            traceback.print_exc()
        print("after 2nd send enabled", [m.__name__ for m in tab.enabled_domains])
        r = await asyncio.wait_for(tab.send(cdp.runtime.evaluate("2+2")), 10)
        print("3rd send", r[0].value)
    finally:
        await browser.stop()

asyncio.run(asyncio.wait_for(main(), 50))
