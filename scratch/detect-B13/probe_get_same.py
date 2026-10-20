import asyncio, time, threading, http.server
import zendriver as zd
class H(http.server.BaseHTTPRequestHandler):
    def log_message(self, *a): pass
    def do_GET(self):
        if self.path.startswith("/204"):
            self.send_response(204); self.end_headers(); return
        body = b"<html><head><title>t</title></head><body>page</body></html>"
        self.send_response(200); self.send_header("Content-Type", "text/html"); self.send_header("Content-Length", str(len(body))); self.end_headers(); self.wfile.write(body)
async def main():
    srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), H)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    base = f"http://127.0.0.1:{srv.server_address[1]}"
    browser = await zd.start(headless=True)
    try:
        for label, url in [("first", base + "/a"), ("same url again", base + "/a"), ("204", base + "/204")]:
            t0 = time.monotonic()
            try:
                await asyncio.wait_for(browser.get(url, timeout=3), 20)
                print(f"{label}: ok {time.monotonic()-t0:.1f}s")
            except asyncio.TimeoutError as e:
                print(f"{label}: TimeoutError {time.monotonic()-t0:.1f}s")
    finally:
        await asyncio.wait_for(browser.stop(), 15)
asyncio.run(main())
