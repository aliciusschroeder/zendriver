import asyncio
import http.server
import threading
import traceback

PAGES: dict = {}


class H(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        body = PAGES.get(self.path.split("?")[0])
        if body is None:
            self.send_response(404)
            self.end_headers()
            return
        if callable(body):
            body = body(self)
        data = body.encode()
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def log_message(self, *a):
        pass


def serve():
    srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), H)
    t = threading.Thread(target=srv.serve_forever, daemon=True)
    t.start()
    return srv, srv.server_address[1]


async def show(label, coro, t=20):
    try:
        r = await asyncio.wait_for(coro, t)
        print(f"[{label}] ->", repr(r))
        return r
    except Exception as e:
        print(f"[{label}] EXC {type(e).__name__}: {str(e)[:200]}")
        return e


def desc(e):
    if e is None:
        return None
    if isinstance(e, list):
        return [desc(x) for x in e]
    return (e.node_name, e.node_type, int(e.backend_node_id))
