import http.server
import threading


def start_server():
    class Handler(http.server.BaseHTTPRequestHandler):
        def do_GET(self) -> None:
            port = server.server_address[1]
            if self.path == "/same":
                body = (
                    "<html><body><div id='inner'><span class='s'>hello same origin</span>"
                    "<b>bold inner</b></div></body></html>"
                )
            elif self.path == "/cross":
                body = "<html><body><p id='crossp'>hello cross site</p></body></html>"
            elif self.path == "/table":
                rows = "".join(
                    f"<tr id='r{i}'><td>cell {i}</td></tr>" for i in range(20)
                )
                body = f"<html><body><table>{rows}</table></body></html>"
            else:
                body = (
                    "<html><body>"
                    "<div id='top'><p id='topp'>top paragraph</p></div>"
                    "<input id='inp' placeholder='type here'>"
                    "<iframe id='same-frame' src='/same'></iframe>"
                    f"<iframe id='cross-frame' src='http://localhost:{port}/cross'></iframe>"
                    "</body></html>"
                )
            data = body.encode()
            self.send_response(200)
            self.send_header("Content-Type", "text/html")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def log_message(self, format, *args):
            pass

    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    t = threading.Thread(target=server.serve_forever, daemon=True)
    t.start()
    return server, f"http://127.0.0.1:{server.server_address[1]}"
