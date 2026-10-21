import asyncio, sys, threading, http.server, gc
import zendriver as zd
from zendriver.core.connection import Listener
print("zendriver from", zd.__file__, "python", sys.version.split()[0])

class H(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        body = b"<html><head><title>t</title></head><body>hi</body></html>"
        self.send_response(200); self.send_header("Content-Type", "text/html")
        self.send_header("Content-Length", str(len(body))); self.end_headers(); self.wfile.write(body)
    def log_message(self, *a): pass

srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), H)
threading.Thread(target=srv.serve_forever, daemon=True).start()
URL = f"http://127.0.0.1:{srv.server_address[1]}/"

zombies = []
_init = Listener.__init__
def init(self, connection):
    if connection.websocket is None:
        zombies.append(connection)
    _init(self, connection)
Listener.__init__ = init

async def main():
    browser = await zd.start(headless=True)
    try:
        tab = await browser.get(URL, new_tab=True)
        async def closer():
            while tab.session_id is None:
                await asyncio.sleep(0)
            await tab.aclose()
        r = await asyncio.wait_for(asyncio.gather(tab.evaluate("1"), closer(), return_exceptions=True), 20)
        print("first send:", repr(r[0])[:80])
        print("_prep_headless_done after detach:", tab.__dict__.get("_prep_headless_done"))
        print("listeners created on a detached session:", len(zombies), "mapper:", len(tab.mapper))
        ua = await asyncio.wait_for(tab.evaluate("navigator.userAgent"), 20)
        print("UA after reattach (session %s): %s" % (tab.session_id, ua))
        print("HeadlessChrome leaked:", "Headless" in ua)
    finally:
        await browser.stop()
    srv.shutdown()

asyncio.run(main())
