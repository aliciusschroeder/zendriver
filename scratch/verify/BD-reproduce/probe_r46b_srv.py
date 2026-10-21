import threading, http.server, socketserver
PAGE = b"""<!doctype html><html><body><script>
window.__a=null; window.__b=null;
fetch('/a.json').then(r=>r.text()).then(t=>window.__a=t);
setTimeout(()=>fetch('/b.json').then(r=>r.text()).then(t=>window.__b=t), 300);
</script></body></html>"""
class H(http.server.BaseHTTPRequestHandler):
    def log_message(self, *a): pass
    def do_GET(self):
        if self.path.startswith("/page"):
            body, ct = PAGE, "text/html"
        elif self.path.startswith("/a.json"):
            body, ct = b'{"a":1}', "application/json"
        elif self.path.startswith("/b.json"):
            body, ct = b'{"b":2}', "application/json"
        else:
            self.send_response(404); self.end_headers(); return
        self.send_response(200); self.send_header("Content-Type", ct); self.send_header("Content-Length", str(len(body))); self.end_headers(); self.wfile.write(body)
srv = socketserver.ThreadingTCPServer(("127.0.0.1", 0), H); srv.daemon_threads = True
threading.Thread(target=srv.serve_forever, daemon=True).start()
BASE = f"http://127.0.0.1:{srv.server_address[1]}"
