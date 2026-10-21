import http.server, threading, time

UA_LOG = []

class H(http.server.BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass
    def do_GET(self):
        UA_LOG.append((self.path, self.headers.get("User-Agent"), self.headers.get("Sec-CH-UA")))
        p = self.path.split("?")[0]
        if p == "/204":
            self.send_response(204); self.end_headers(); return
        if p == "/dl":
            body = b"x" * 1000
            self.send_response(200)
            self.send_header("Content-Type", "application/octet-stream")
            self.send_header("Content-Disposition", "attachment; filename=f.zip")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers(); self.wfile.write(body); return
        if p == "/hang":
            time.sleep(30); return
        if p == "/favicon.ico":
            self.send_response(404); self.end_headers(); return
        body = (b"<html><head><title>%s</title><script>window.__ua=navigator.userAgent;"
                b"window.__shadow=(function(){var d=document.createElement('div');"
                b"var s=d.attachShadow({mode:'closed'});return d.shadowRoot!==null})();</script>"
                b"</head><body>page %s</body></html>") % (p.encode(), p.encode())
        self.send_response(200)
        self.send_header("Content-Type", "text/html")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers(); self.wfile.write(body)

def start():
    s = http.server.ThreadingHTTPServer(("127.0.0.1", 0), H)
    s.daemon_threads = True
    threading.Thread(target=s.serve_forever, daemon=True).start()
    return s, f"http://127.0.0.1:{s.server_address[1]}"
