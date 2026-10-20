import asyncio, threading, http.server, functools, os
import zendriver as zd
from zendriver import cdp

def serve():
    d = os.path.join(os.path.dirname(os.path.abspath(__file__)), "www")
    class Q(http.server.SimpleHTTPRequestHandler):
        def log_message(self, *a): pass
    srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), functools.partial(Q, directory=d))
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv.server_address[1]

async def main():
    url = f"http://127.0.0.1:{serve()}/index.html"
    browser = await zd.start(headless=True)
    try:
        tab = browser.main_tab
        async with tab.expect_response(url) as r:
            await tab.get(url)
            await asyncio.wait_for(r.value, 5)
        loaded = asyncio.Event()
        tab.add_handler(cdp.page.LoadEventFired, lambda e: None)
        try:
            await tab.reload()
            print("reload OK")
        except Exception as e:
            print("tab.reload() after expect_response raised:", type(e).__name__, e)
    finally:
        await browser.stop()
asyncio.run(asyncio.wait_for(main(), 50))
