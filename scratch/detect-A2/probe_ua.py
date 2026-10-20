import asyncio, threading, http.server
import zendriver as zd
from zendriver import cdp

seen = []
class H(http.server.BaseHTTPRequestHandler):
    def log_message(self, *a): pass
    def do_GET(self):
        seen.append((self.path, self.headers.get("User-Agent"), self.headers.get("Sec-Fetch-Dest")))
        body = b"<html>hi</html>"
        self.send_response(200); self.send_header("Content-Type", "text/html"); self.send_header("Content-Length", str(len(body))); self.end_headers(); self.wfile.write(body)

async def main():
    srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), H)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    base = f"http://127.0.0.1:{srv.server_address[1]}"
    browser = await zd.start(headless=True)
    try:
        t1 = await browser.get(base + "/main-tab")
        t2 = await browser.get(base + "/new-tab", new_tab=True)
        await asyncio.sleep(0.5)
        ua_js = await t2.evaluate("navigator.userAgent")
        print("navigator.userAgent in new tab after first send:", ua_js)
        await t2.reload()
        await asyncio.sleep(0.5)
    finally:
        await browser.stop()
    for p, ua, dest in seen:
        if dest == "document":
            print(p, "Headless" in (ua or ""), ua)

asyncio.run(asyncio.wait_for(main(), 50))
