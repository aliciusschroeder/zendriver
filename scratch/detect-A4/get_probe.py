import asyncio, time, http.server, threading, os
import zendriver as zd
from zendriver import cdp

class H(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        body = b"<html><head><title>same</title></head><body>hi</body></html>"
        self.send_response(200); self.send_header("Content-Type","text/html"); self.send_header("Content-Length", str(len(body))); self.end_headers(); self.wfile.write(body)
    def log_message(self, *a): pass
srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), H)
threading.Thread(target=srv.serve_forever, daemon=True).start()
URL = f"http://127.0.0.1:{srv.server_address[1]}/page"

async def timed(label, coro):
    t = time.time()
    try:
        r = await coro
        print(f"{label}: OK in {time.time()-t:.2f}s -> {r}")
    except BaseException as e:
        print(f"{label}: {type(e).__name__} after {time.time()-t:.2f}s {e}")

async def main():
    b = await zd.start(headless=True)
    try:
        await timed("get(about:blank) on fresh tab", b.get("about:blank", timeout=4))
        await timed("get(URL)", b.get(URL, timeout=4))
        await asyncio.sleep(0.5)
        await timed("get(URL) again (same url)", b.get(URL, timeout=4))
        await timed("get(URL#frag)", b.get(URL + "#frag", timeout=4))
        await timed("get(new_tab=True) default about:blank", b.get(new_tab=True, timeout=4))
        await timed("get(about:blank) from URL page", b.get("about:blank", timeout=4))
        await timed("get(about:blank) again", b.get("about:blank", timeout=4))
    finally:
        await b.stop()
asyncio.run(main())
