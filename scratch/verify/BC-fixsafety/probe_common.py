import http.server
import threading

PAGES: dict[str, str] = {}


def serve() -> tuple[http.server.ThreadingHTTPServer, int]:
    class H(http.server.BaseHTTPRequestHandler):
        def do_GET(self) -> None:
            path = self.path.split("?")[0]
            body = PAGES.get(path)
            if body is None:
                self.send_response(404)
                self.end_headers()
                return
            port = self.server.server_address[1]
            data = body.replace("{PORT}", str(port)).encode()
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def log_message(self, *a: object) -> None:
            pass

    srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), H)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv, srv.server_address[1]


PAGES["/main"] = """<!doctype html><html><body>
<div id="top"><p id="topp">top paragraph</p></div>
<div id="outer"><div id="inner2">x</div><p id="deep"><b id="bold">bold</b></p></div>
<iframe id="fr" src="/same"></iframe>
<iframe id="sd" srcdoc="<div id=box><p id=inner data-v=1>srcdoc inner</p></div>"></iframe>
<iframe id="cross" src="http://localhost:{PORT}/cross"></iframe>
</body></html>"""

PAGES["/same"] = """<!doctype html><html><body>
<div id="inner"><span class="s">hello same origin</span><b>bold inner</b></div>
<button onclick="window.clicked=(window.clicked||0)+1">inner needle</button>
<input placeholder="Search needle">
<div id="host"></div>
<script>document.getElementById('host').attachShadow({mode:'open'}).innerHTML='<b>shadow needle</b>';</script>
</body></html>"""

PAGES["/cross"] = """<!doctype html><html><body><p>cross para</p></body></html>"""

PAGES["/text"] = """<!doctype html><html><body>
<button title="Login">Login</button>
<p id="p1">needle <b>x</b> needle</p>
<a href="#">needle link</a>
<p id="topp">top paragraph</p>
</body></html>"""

PAGES["/rows"] = (
    "<!doctype html><html><body><table>"
    + "".join(f"<tr><td>c{i}</td></tr>" for i in range(20))
    + "</table><p id='topp'>top paragraph</p></body></html>"
)
