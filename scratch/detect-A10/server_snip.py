class H(http.server.BaseHTTPRequestHandler):
    def log_message(self, *a): pass
    def do_GET(self):
        if self.path.startswith("/page"):
            b = b"<html><body><script>fetch('/a.json').then(r=>r.text()).then(t=>window.__a=t); fetch('/b.json').then(r=>r.text()).then(t=>window.__b=t);</script></body></html>"
            ct = "text/html"
        else:
            b = ('{"file":"%s"}' % self.path).encode(); ct = "application/json"
        self.send_response(200); self.send_header("Content-Type", ct); self.send_header("Content-Length", str(len(b))); self.end_headers(); self.wfile.write(b)
srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), H)
port = srv.server_address[1]
threading.Thread(target=srv.serve_forever, daemon=True).start()
BASE = f"http://127.0.0.1:{port}"
async def w(aw, t=5):
    try:
        return await asyncio.wait_for(aw, t)
    except asyncio.TimeoutError:
        return "TIMEOUT"
    except Exception as e:
        return f"{type(e).__name__}: {str(e).splitlines()[0]}"
