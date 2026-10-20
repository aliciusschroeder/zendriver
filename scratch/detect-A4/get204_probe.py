import asyncio, time, http.server, threading
import zendriver as zd
from zendriver import cdp

class H(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/204":
            self.send_response(204); self.end_headers(); return
        if self.path == "/dl":
            body = b"x" * 10
            self.send_response(200); self.send_header("Content-Disposition", "attachment; filename=a.bin")
            self.send_header("Content-Type", "application/octet-stream"); self.send_header("Content-Length", "10"); self.end_headers(); self.wfile.write(body); return
        body = b"<title>p</title>page"
        self.send_response(200); self.send_header("Content-Type","text/html"); self.send_header("Content-Length", str(len(body))); self.end_headers(); self.wfile.write(body)
    def log_message(self, *a): pass
srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), H)
threading.Thread(target=srv.serve_forever, daemon=True).start()
B = f"http://127.0.0.1:{srv.server_address[1]}"

async def timed(label, coro):
    t = time.time()
    try:
        r = await coro
        print(f"{label}: OK in {time.time()-t:.2f}s -> {r}")
    except BaseException as e:
        print(f"{label}: {type(e).__name__} after {time.time()-t:.2f}s {e!r}"[:200])

async def main():
    b = await zd.start(headless=True)
    try:
        await timed("get(page)", b.get(B + "/page", timeout=3))
        await timed("get(204)", b.get(B + "/204", timeout=3))
        await timed("get(download)", b.get(B + "/dl", timeout=3))
        t = b.tabs[0]
        await timed("tab.get(204)", t.get(B + "/204"))
    finally:
        await b.stop()
asyncio.run(main())
