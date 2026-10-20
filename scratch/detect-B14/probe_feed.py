import asyncio, sys, threading, http.server, functools, os, gc
import zendriver as zd
from zendriver import cdp

def serve():
    d = os.path.join(os.path.dirname(os.path.abspath(__file__)), "www")
    class Q(http.server.SimpleHTTPRequestHandler):
        def log_message(self, *a): pass
    srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), functools.partial(Q, directory=d))
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv.server_address[1]

async def main(kind):
    port = serve()
    url = f"http://127.0.0.1:{port}/index.html"
    browser = await zd.start(headless=True)
    try:
        tab = browser.main_tab
        calls = []
        def sync_handler(ev: cdp.fetch.RequestPaused, t):
            calls.append(ev.request_id)
            try:
                t.feed_cdp(cdp.fetch.continue_request(request_id=ev.request_id))
            except BaseException as e:
                print("feed_cdp raised in handler thread:", type(e).__name__, e, flush=True)
                raise
        async def async_handler(ev: cdp.fetch.RequestPaused, t):
            calls.append(ev.request_id)
            t.feed_cdp(cdp.fetch.continue_request(request_id=ev.request_id))
        tab.add_handler(cdp.fetch.RequestPaused, sync_handler if kind == "sync" else async_handler)
        await tab.send(cdp.fetch.enable())
        try:
            await asyncio.wait_for(tab.send(cdp.page.navigate(url)), 5)
            await asyncio.sleep(1)
            title = await asyncio.wait_for(tab.evaluate("document.title"), 5)
            print("kind=%s handler calls=%d title=%r" % (kind, len(calls), title))
        except asyncio.TimeoutError:
            print("kind=%s handler calls=%d -> navigation HUNG (timeout)" % (kind, len(calls)))
    finally:
        await browser.stop()
    gc.collect()

asyncio.run(asyncio.wait_for(main(sys.argv[1]), 50))
