import asyncio
import http.server
import threading

import zendriver as zd
from zendriver import cdp

print("zendriver from", zd.__file__)


async def main():
    srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), http.server.SimpleHTTPRequestHandler)
    srv.RequestHandlerClass.log_message = lambda *a: None
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    url = f"http://127.0.0.1:{srv.server_address[1]}/"
    browser = await zd.start(headless=True)
    try:
        t = await asyncio.wait_for(browser.get(url, new_tab=True), 20)
        print("Browser.get(new_tab) history.length:", await t.evaluate("history.length"))
        for initial in ("about:blank", ""):
            tid = await browser.connection.send(cdp.target.create_target(initial))
            tab = await browser._get_tab(tid)
            await tab.send(cdp.page.navigate(url))
            await tab.sleep(0.5)
            print(f"createTarget({initial!r}) + navigate history.length:", await tab.evaluate("history.length"))
        # initial main tab, navigated with Page.navigate
        t0 = browser.tabs[0]
        await t0.send(cdp.page.navigate(url))
        await t0.sleep(0.5)
        print("main tab (started at about:blank by command line) + navigate:", await t0.evaluate("history.length"))
    finally:
        await browser.stop()
        srv.shutdown()


asyncio.run(main())
