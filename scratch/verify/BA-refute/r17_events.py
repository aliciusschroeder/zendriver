import asyncio, time, sys, threading, http.server, socketserver
import zendriver as zd
from zendriver import cdp
print("zendriver from", zd.__file__, sys.version.split()[0])
class H(http.server.BaseHTTPRequestHandler):
    def log_message(self, *a): pass
    def do_GET(self):
        if self.path.startswith("/slow"): time.sleep(3)
        if self.path.startswith("/204"):
            self.send_response(204); self.end_headers(); return
        body=b"no title here"; self.send_response(200); self.send_header("Content-Type","text/html"); self.send_header("Content-Length", str(len(body))); self.end_headers(); self.wfile.write(body)
class TS(socketserver.ThreadingMixIn, http.server.HTTPServer): daemon_threads = True
srv = TS(("127.0.0.1", 0), H); threading.Thread(target=srv.serve_forever, daemon=True).start()
B = f"http://127.0.0.1:{srv.server_address[1]}"
async def main():
    b = await zd.start(headless=True)
    evs = []
    t0 = time.monotonic()
    async def h(ev):
        ti = getattr(ev, "target_info", None)
        evs.append((round(time.monotonic()-t0, 2), type(ev).__name__, ti.url if ti else getattr(ev, "target_id", "")))
    b.connection.add_handler(cdp.target.TargetCreated, h)
    b.connection.add_handler(cdp.target.TargetInfoChanged, h)
    try:
        for path in ["/notitle", "/slow", "/204"]:
            evs.clear(); t0 = time.monotonic(); t = time.monotonic()
            try:
                await asyncio.wait_for(b.get(B + path, new_tab=True, timeout=6), 15); r = "OK"
            except Exception as e: r = type(e).__name__
            print(f"new_tab {path}: {r} in {time.monotonic()-t:.2f}s events={evs}")
    finally:
        await b.stop(); srv.shutdown()
asyncio.run(main())
