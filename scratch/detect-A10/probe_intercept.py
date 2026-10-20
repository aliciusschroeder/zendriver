import asyncio, threading, http.server, os, sys
import zendriver as zd
from zendriver.cdp.fetch import RequestStage
from zendriver.cdp.network import ResourceType
exec(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "server_snip.py")).read())
XHR = ResourceType.XHR
async def main():
    loop = asyncio.get_running_loop()
    loop.set_exception_handler(lambda l, ctx: print("LOOP ERR:", repr(ctx.get("exception"))))
    browser = await zd.start(headless=True, browser_connection_timeout=1.0, browser_connection_max_tries=30)
    tab = browser.main_tab
    await tab.get("about:blank")
    print("== scenario 1: nested intercepts")
    async with tab.intercept("*a.json*", RequestStage.REQUEST, XHR) as a:
        async with tab.intercept("*b.json*", RequestStage.REQUEST, XHR) as b:
            await tab.get(BASE + "/page1")
            ra = await w(asyncio.shield(a.request)); rb = await w(asyncio.shield(b.request))
            print("outer a.request:", getattr(ra, "url", ra))
            print("inner b.request:", getattr(rb, "url", rb))
            print("a.continue_request:", await w(a.continue_request()))
            print("b.continue_request:", await w(b.continue_request()))
    await asyncio.sleep(0.5)
    print("window.__a/__b:", await tab.evaluate("[window.__a, window.__b]"))

    print("== scenario 2: inner intercept exits before outer matched")
    async with tab.intercept("*a.json*", RequestStage.REQUEST, XHR) as a:
        async with tab.intercept("*b.json*", RequestStage.REQUEST, XHR) as b:
            pass
        print("fetch in manual domains:", zd.cdp.fetch in tab.manually_enabled_domains, "handlers:", len(tab.handlers.get(zd.cdp.fetch.RequestPaused, [])))
        r = await w(tab.get(BASE + "/page2"), 8)
        print("tab.get ->", r if isinstance(r, str) else "ok")
        ra = await w(asyncio.shield(a.request))
        print("outer a.request:", getattr(ra, "url", ra))
        await w(a.continue_request())
        await asyncio.sleep(1)
        print("window.__a/__b inside outer:", await w(tab.evaluate("[window.__a, window.__b]")))
    await browser.stop()
asyncio.run(main())
