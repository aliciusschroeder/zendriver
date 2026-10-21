import asyncio, sys, pathlib, threading, functools, http.server
import zendriver as zd
from zendriver import cdp
from zendriver.cdp.fetch import RequestStage
from zendriver.cdp.network import ResourceType
HERE = pathlib.Path(__file__).parent
class Q(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *a): print("HTTP", a[1] if len(a)>1 else a)
srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), functools.partial(Q, directory=str(HERE / "www")))
threading.Thread(target=srv.serve_forever, daemon=True).start()
BASE = f"http://127.0.0.1:{srv.server_address[1]}"
async def main():
    browser = await zd.start(headless=True)
    try:
        tab = await browser.get(BASE + "/page.html"); await tab.sleep(0.5)
        print("title", await tab.evaluate("document.title"), tab.url)
        await tab.evaluate("window.__a=null; fetch('/a.json').then(r=>r.text()).then(t=>window.__a=t).catch(e=>window.__a='ERR '+e)")
        await asyncio.sleep(1); print("no intercept __a:", await tab.evaluate("window.__a"))
        seen = []
        tab.add_handler(cdp.fetch.RequestPaused, lambda e: seen.append((e.request.url, e.resource_type)))
        await tab.send(cdp.fetch.enable([cdp.fetch.RequestPattern(url_pattern="*a.json*", request_stage=RequestStage.REQUEST)]))
        await tab.evaluate("window.__a=null; fetch('/a.json?x').then(r=>r.text()).then(t=>window.__a=t).catch(e=>window.__a='ERR '+e)")
        await asyncio.sleep(2); print("seen", seen)
    finally:
        await browser.stop(); srv.shutdown()
asyncio.run(main())
