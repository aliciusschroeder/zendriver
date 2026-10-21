import http.server, threading, socketserver, socket, time

POLL_PAGE = b"""<html><body>poll<script>
setInterval(()=>{fetch('/poll?t='+Date.now()).catch(()=>{})}, 300);
</script></body></html>"""

BROKEN_PAGE = b"""<html><body>broken<script>
fetch('/api.json').then(r=>r.text()).then(t=>{document.title='ok:'+t.length}).catch(e=>{document.title='err:'+e});
</script></body></html>"""

REFUSED_PAGE = b"""<html><body>refused<script>
fetch('http://127.0.0.1:1/x').catch(e=>{document.title='err:'+e});
</script></body></html>"""

class H(http.server.BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"
    def log_message(self, *a): pass
    def _send(self, body, ctype="text/html"):
        self.send_response(200)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)
    def do_GET(self):
        p = self.path.split("?")[0]
        if p == "/poll_page":
            self._send(POLL_PAGE)
        elif p == "/poll":
            self._send(b"{}", "application/json")
        elif p == "/broken_page":
            self._send(BROKEN_PAGE)
        elif p == "/refused_page":
            self._send(REFUSED_PAGE)
        elif p == "/api.json":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", "1000")
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(b'{"a":"1234')
            self.wfile.flush()
            self.close_connection = True
            try:
                self.connection.shutdown(socket.SHUT_RDWR)
            except Exception:
                pass
        else:
            self._send(("<html><head><title>%s</title></head><body>page %s</body></html>" % (p, p)).encode())

class TS(socketserver.ThreadingMixIn, http.server.HTTPServer):
    daemon_threads = True
    allow_reuse_address = True

def start_server():
    srv = TS(("127.0.0.1", 0), H)
    t = threading.Thread(target=srv.serve_forever, daemon=True)
    t.start()
    return srv, "http://127.0.0.1:%d" % srv.server_address[1]
