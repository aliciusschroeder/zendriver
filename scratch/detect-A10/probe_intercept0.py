import asyncio, threading, http.server, os, sys
import zendriver as zd
from zendriver.cdp.fetch import RequestStage
from zendriver.cdp.network import ResourceType
exec(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "server_snip.py")).read())

async def main():
    browser = await zd.start(headless=True, browser_connection_timeout=1.0, browser_connection_max_tries=30)
    tab = browser.main_tab
    await tab.get("about:blank")
    seen = []
    tab.add_handler(zd.cdp.network.RequestWillBeSent, lambda e: seen.append((e.type_, e.request.url)))
    for rt in [ResourceType.FETCH, ResourceType.XHR, None]:
        async with tab.intercept("*a.json*", RequestStage.REQUEST, rt) as a:
            await tab.get(BASE + "/page1")
            ra = await w(asyncio.shield(a.request))
            print(rt, "single a.request:", getattr(ra, "url", ra))
            if not isinstance(ra, str):
                await a.continue_request()
    print(seen[:6])
    await browser.stop()
asyncio.run(main())
