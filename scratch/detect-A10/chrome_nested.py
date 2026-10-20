import asyncio, threading, functools, http.server, socketserver
import zendriver as zd
from zendriver.cdp.fetch import RequestStage
from zendriver.cdp.network import ResourceType
Handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory="www")
class Q(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *a): pass
srv = socketserver.TCPServer(("127.0.0.1", 0), functools.partial(Q, directory="www"))
threading.Thread(target=srv.serve_forever, daemon=True).start()
BASE = f"http://127.0.0.1:{srv.server_address[1]}"
async def main():
    b = await zd.start(headless=True)
    try:
        tab = b.main_tab
        async with tab.intercept("*/a.png", RequestStage.REQUEST, ResourceType.IMAGE) as ia:
            async with tab.intercept("*/b.png", RequestStage.REQUEST, ResourceType.IMAGE) as ib:
                await tab.get(BASE + "/two.html")
                ra = await asyncio.wait_for(ia.request, 5)
                rb = await asyncio.wait_for(ib.request, 5)
                print("ia (pattern */a.png) got:", ra.url.rsplit('/',1)[-1])
                print("ib (pattern */b.png) got:", rb.url.rsplit('/',1)[-1])
                await ib.continue_request()
                try:
                    await ia.continue_request()
                    print("ia.continue_request ok")
                except Exception as e:
                    print("ia.continue_request raised:", type(e).__name__, str(e).splitlines()[0])
    finally:
        await b.stop()
        srv.shutdown()
asyncio.run(asyncio.wait_for(main(), 60))
