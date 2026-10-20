import asyncio, threading, http.server, functools, os, base64, struct
import zendriver as zd
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, "site")
def serve():
    class H(http.server.SimpleHTTPRequestHandler):
        def log_message(self, *a): pass
    srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), functools.partial(H, directory=ROOT))
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv
def dims(b64):
    b = base64.b64decode(b64)
    return struct.unpack(">II", b[16:24])
async def main():
    srv = serve()
    base = f"http://127.0.0.1:{srv.server_address[1]}"
    for headless in (True,):
        browser = await zd.start(headless=headless)
        try:
            tab = await browser.get(base + "/tall.html")
            await tab.wait_for_ready_state("complete")
            print("viewport:", await tab.evaluate("[innerWidth, innerHeight, document.documentElement.scrollWidth, document.documentElement.scrollHeight]", return_by_value=True))
            print("viewport shot:", dims(await tab.screenshot_b64(format="png")))
            print("full_page shot:", dims(await tab.screenshot_b64(format="png", full_page=True)))
            await tab.scroll_down(50)
            await asyncio.sleep(0.5)
            print("scrollY", await tab.evaluate("scrollY"))
            print("full_page shot after scroll:", dims(await tab.screenshot_b64(format="png", full_page=True)))
        finally:
            await browser.stop()
    srv.shutdown()
asyncio.run(asyncio.wait_for(main(), 100))
