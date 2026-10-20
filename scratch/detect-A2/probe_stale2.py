import asyncio, threading, http.server
import zendriver as zd
from zendriver import cdp

class H(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *a): pass
    def do_GET(self):
        body = b"<html>hi</html>"
        self.send_response(200); self.send_header("Content-Length", str(len(body))); self.end_headers(); self.wfile.write(body)

async def main():
    srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), H)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    base = f"http://127.0.0.1:{srv.server_address[1]}/"
    browser = await zd.start(headless=True)
    try:
        tab = await browser.get(base)
        async with tab.expect_request(base + "*") as req:
            await tab.reload()
            print("expected request:", (await req.request).url)
        async def on_load(e): pass
        tab.add_handler(cdp.page.LoadEventFired, on_load)
        try:
            await asyncio.wait_for(tab.reload(), 10)
            print("reload ok")
        except Exception as e:
            print("tab.reload() raised", type(e).__name__, e)
    finally:
        await browser.stop()

asyncio.run(asyncio.wait_for(main(), 50))
