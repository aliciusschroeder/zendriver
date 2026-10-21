import asyncio, functools, http.server, sys, threading
import zendriver
from zendriver import cdp
from zendriver.cdp.fetch import RequestStage
from zendriver.cdp.network import ResourceType
print("zendriver from", zendriver.__file__)
D = sys.argv[1]
class Q(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *a): pass
srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), functools.partial(Q, directory=f"{D}/www"))
threading.Thread(target=srv.serve_forever, daemon=True).start()
base = f"http://127.0.0.1:{srv.server_address[1]}"
async def main():
    browser = await zendriver.start(headless=True)
    try:
        tab = await browser.get("about:blank")
        # scenario 1: nested
        async with tab.intercept("*a.json*", RequestStage.REQUEST, ResourceType.XHR) as a:
            async with tab.intercept("*b.json*", RequestStage.REQUEST, ResourceType.XHR) as b:
                await tab.get(base + "/page.html")
                ra = await asyncio.wait_for(a.request, 10)
                rb = await asyncio.wait_for(b.request, 10)
                print("S1 outer a.request.url:", ra.url, "| inner b.request.url:", rb.url)
                try:
                    await asyncio.wait_for(a.continue_request(), 5); print("S1 a.continue_request OK")
                except Exception as e: print("S1 a.continue_request EXC", type(e).__name__, str(e).splitlines()[0])
                try:
                    await asyncio.wait_for(b.continue_request(), 5); print("S1 b.continue_request OK")
                except Exception as e: print("S1 b.continue_request EXC", type(e).__name__, str(e).splitlines()[0])
            await asyncio.sleep(0.5)
        print("S1 page values:", await tab.evaluate("[window.__a, window.__b]"))
        # scenario 2: inner exits first
        tab = await browser.get("about:blank", new_tab=True)
        async with tab.intercept("*a.json*", RequestStage.REQUEST, ResourceType.XHR) as a:
            async with tab.intercept("*b.json*", RequestStage.REQUEST, ResourceType.XHR) as b:
                pass
            print("S2 fetch manual:", cdp.fetch in tab.manually_enabled_domains, "handlers:", len(tab.handlers.get(cdp.fetch.RequestPaused, [])))
            try:
                await asyncio.wait_for(tab.get(base + "/page2.html"), 8); print("S2 tab.get OK")
            except asyncio.TimeoutError:
                print("S2 tab.get TIMEOUT (8s)")
            if a.response_future.done():
                ev = a.response_future.result()
                print("S2 outer a resolved with:", ev.request.url, ev.resource_type)
            else:
                print("S2 outer a not resolved")
            # cleanup: continue everything paused
        await asyncio.sleep(0.3)
    finally:
        await asyncio.wait_for(browser.stop(), 30)
        srv.shutdown()
asyncio.run(main())
