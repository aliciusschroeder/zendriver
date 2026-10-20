import asyncio, sys, threading, http.server, functools, os
import zendriver as zd
from zendriver import cdp

def serve():
    h = functools.partial(http.server.SimpleHTTPRequestHandler, directory=os.path.join(os.path.dirname(os.path.abspath(__file__)), "www"))
    class Q(h.func):
        def log_message(self, *a): pass
    srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), functools.partial(Q, directory=h.keywords["directory"]))
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv.server_address[1]

async def main(mode):
    port = serve()
    url = f"http://127.0.0.1:{port}/index.html"
    browser = await zd.start(headless=True, expert=True)
    try:
        tab = await browser.get(url, new_tab=True)   # no send on the new tab yet
        await asyncio.sleep(1)
        if mode == "seq":
            await tab.evaluate("1"); await tab.evaluate("2")
        elif mode == "gather":
            await asyncio.gather(tab.evaluate("1"), tab.evaluate("2"))
        elif mode == "localstorage":
            await tab.set_local_storage({"a": "1", "b": "2"})
        await tab.reload()
        await asyncio.sleep(1)
        title = await tab.evaluate("document.title")
        print("mode=%s title=%r" % (mode, title))
    finally:
        await browser.stop()

asyncio.run(asyncio.wait_for(main(sys.argv[1]), 50))
