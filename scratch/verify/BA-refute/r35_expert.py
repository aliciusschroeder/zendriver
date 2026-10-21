import asyncio, sys, threading, http.server, socketserver
import zendriver as zd
print("zendriver from", zd.__file__, sys.version.split()[0])
log = []
class H(http.server.BaseHTTPRequestHandler):
    def log_message(self, *a): pass
    def do_GET(self):
        log.append(self.path)
        if self.path.startswith("/beacon"):
            self.send_response(204); self.end_headers(); return
        body = (b"<div id=d></div><script>var r=document.getElementById('d').attachShadow({mode:'closed'});"
                b"new Image().src='/beacon?from=" + self.path.encode() + b"&open='+(document.getElementById('d').shadowRoot!==null);</script>")
        self.send_response(200); self.send_header("Content-Type","text/html"); self.send_header("Content-Length", str(len(body))); self.end_headers(); self.wfile.write(body)
class TS(socketserver.ThreadingMixIn, http.server.HTTPServer):
    daemon_threads = True
srv = TS(("127.0.0.1", 0), H)
threading.Thread(target=srv.serve_forever, daemon=True).start()
B = f"http://127.0.0.1:{srv.server_address[1]}"
async def main():
    b = await zd.start(headless=True, expert=True)
    try:
        await b.get(B + "/main-tab"); await asyncio.sleep(0.5)
        t1 = await b.get(B + "/new-tab", new_tab=True); await asyncio.sleep(0.5)
        await t1.reload(); await asyncio.sleep(0.5)
        for e in log:
            if "beacon" in e: print(e)
    finally:
        await b.stop(); srv.shutdown()
asyncio.run(main())
