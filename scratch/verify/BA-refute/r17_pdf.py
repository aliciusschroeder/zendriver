import asyncio, time, sys, threading, http.server, socketserver
import zendriver as zd
from zendriver import cdp
print("zendriver from", zd.__file__, sys.version.split()[0])
PDF = b"%PDF-1.1\n1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj 2 0 obj<</Type/Pages/Kids[3 0 R]/Count 1>>endobj 3 0 obj<</Type/Page/Parent 2 0 R/MediaBox[0 0 100 100]>>endobj\ntrailer<</Root 1 0 R>>\n%%EOF"
class H(http.server.BaseHTTPRequestHandler):
    def log_message(self, *a): pass
    def do_GET(self):
        if self.path.startswith("/x.pdf"):
            self.send_response(200); self.send_header("Content-Type","application/pdf"); self.send_header("Content-Length", str(len(PDF))); self.end_headers(); self.wfile.write(PDF)
        else:
            body=b"<title>p</title>"; self.send_response(200); self.send_header("Content-Type","text/html"); self.send_header("Content-Length", str(len(body))); self.end_headers(); self.wfile.write(body)
class TS(socketserver.ThreadingMixIn, http.server.HTTPServer): daemon_threads = True
srv = TS(("127.0.0.1", 0), H); threading.Thread(target=srv.serve_forever, daemon=True).start()
B = f"http://127.0.0.1:{srv.server_address[1]}"
async def main():
    b = await zd.start(headless=True)
    try:
        await b.get(B + "/p")
        t = time.monotonic()
        print("raw navigate pdf:", await b.tabs[0].send(cdp.page.navigate(B + "/x.pdf")))
        await b.get(B + "/p")
        t = time.monotonic()
        try:
            await asyncio.wait_for(b.get(B + "/x.pdf", timeout=3), 10); print(f"browser.get(pdf) OK {time.monotonic()-t:.2f}s")
        except Exception as e: print(f"browser.get(pdf) {type(e).__name__} {time.monotonic()-t:.2f}s")
    finally:
        await b.stop(); srv.shutdown()
asyncio.run(main())
