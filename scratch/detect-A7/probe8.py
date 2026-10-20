import asyncio, threading, http.server, functools, os
import zendriver as zd
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, "site")
def serve():
    class H(http.server.SimpleHTTPRequestHandler):
        def log_message(self, *a): pass
    srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), functools.partial(H, directory=ROOT))
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv
async def main():
    srv = serve()
    base = f"http://127.0.0.1:{srv.server_address[1]}"
    browser = await zd.start(headless=True)
    try:
        tab = await browser.get(base + "/call.html")
        await tab.wait_for_ready_state("complete")
        loop = asyncio.get_running_loop()
        for kw in ({"selector": "button"}, {"text": "please press"}, {"selector": "#go"}):
            t0 = loop.time()
            try:
                el = await tab(**kw, timeout=3)
                print(kw, "->", el, "after %.1fs" % (loop.time() - t0))
            except Exception as e:
                print(kw, "raised", type(e).__name__, str(e)[:80], "after %.1fs" % (loop.time() - t0))
        print("wait_for(selector='button') ->", await tab.wait_for(selector="button", timeout=3))
        print("wait_for(text='please press') ->", await tab.wait_for(text="please press", timeout=3))
    finally:
        await browser.stop(); srv.shutdown()
asyncio.run(asyncio.wait_for(main(), 100))
