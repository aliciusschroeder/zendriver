import asyncio
import zendriver as zd
from zendriver import cdp

async def main():
    b = await zd.start(headless=True)
    try:
        main = b.main_tab
        # set a cookie in default context via browser connection
        await b.connection.send(cdp.storage.set_cookies([cdp.network.CookieParam(name="default_ctx", value="1", domain="example.com", path="/")]))
        ctx_tab = await b.create_context("about:blank")
        await ctx_tab.send(cdp.storage.set_cookies([cdp.network.CookieParam(name="incognito_ctx", value="1", domain="example.com", path="/")]))
        print("main tab closed?", main.closed, "ctx tab closed?", ctx_tab.closed)
        print("tabs:", b.tabs)
        print("browser.cookies.get_all():", [c.name for c in await b.cookies.get_all()])
        print("via browser conn:", [c.name for c in await b.connection.send(cdp.storage.get_cookies())])
        await b.cookies.clear()
        print("after browser.cookies.clear(): default ctx:", [c.name for c in await b.connection.send(cdp.storage.get_cookies())],
              "incognito ctx:", [c.name for c in await ctx_tab.send(cdp.storage.get_cookies())])
        # now use the main tab once, and the same call changes meaning
        await b.connection.send(cdp.storage.set_cookies([cdp.network.CookieParam(name="incognito_again", value="1", domain="example.com", path="/")]))
        await main.send(cdp.runtime.evaluate("1"))
        print("after main tab used once, get_all():", [c.name for c in await b.cookies.get_all()])
    finally:
        await b.stop()
asyncio.run(main())
