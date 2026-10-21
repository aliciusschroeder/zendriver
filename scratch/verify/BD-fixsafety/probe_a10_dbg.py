import asyncio, functools, http.server, sys, threading
import zendriver
from zendriver import cdp
from zendriver.cdp.fetch import RequestStage
from zendriver.cdp.network import ResourceType
D = sys.argv[1]; RT = getattr(ResourceType, sys.argv[2])
class Q(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *a): print("   HTTP", a[1] if len(a)>1 else a)
srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), functools.partial(Q, directory=f"{D}/www"))
threading.Thread(target=srv.serve_forever, daemon=True).start()
base = f"http://127.0.0.1:{srv.server_address[1]}"
async def main():
    browser = await zendriver.start(headless=True)
    try:
        tab = await browser.get("about:blank")
        async def h(ev): print("   RAW RequestPaused", ev.request.url, ev.resource_type)
        async with tab.intercept("*a.json*", RequestStage.REQUEST, RT) as a:
            tab.add_handler(cdp.fetch.RequestPaused, h)
            await tab.get(base + "/page.html")
            try:
                ra = await asyncio.wait_for(a.request, 5); print("single a.request.url:", ra.url)
                await a.continue_request()
            except asyncio.TimeoutError: print("single: timeout")
            tab.remove_handlers(cdp.fetch.RequestPaused, h)
    finally:
        await asyncio.wait_for(browser.stop(), 30); srv.shutdown()
asyncio.run(main())
