import asyncio
import http.server
import threading
import traceback
import contextlib

import zendriver

PAGES: dict = {}


def serve():
    class H(http.server.BaseHTTPRequestHandler):
        def do_GET(self):
            port = self.server.server_address[1]
            path = self.path.split("?")[0]
            body = PAGES.get(path)
            if body is None:
                self.send_response(404)
                self.end_headers()
                return
            if callable(body):
                body = body(port)
            data = body.encode()
            self.send_response(200)
            self.send_header("Content-Type", "text/html")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def log_message(self, *a):
            pass

    srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), H)
    t = threading.Thread(target=srv.serve_forever, daemon=True)
    t.start()
    return srv


def desc(e):
    if e is None:
        return None
    try:
        return f"<{e.node_name} type={e.node_type} bid={e.backend_node_id} id={e.attrs.get('id') if e.node_type == 1 else None!r} val={(e.node_value or '')[:30]!r}>"
    except Exception as ex:
        return f"<desc failed {ex!r}>"


async def step(name, coro, timeout=20):
    try:
        r = await asyncio.wait_for(coro, timeout)
        print(f"[{name}] -> {r}")
        return r
    except Exception as ex:
        print(f"[{name}] EXC {type(ex).__name__}: {ex}")
        return ex


async def wait_loaded(tab, js="document.readyState", want="complete", t=10):
    for _ in range(int(t / 0.1)):
        try:
            r = await tab.evaluate(js)
            if r == want or (want is True and r):
                return True
        except Exception:
            pass
        await asyncio.sleep(0.1)
    return False


@contextlib.asynccontextmanager
async def browser_ctx():
    print("zendriver from", zendriver.__file__)
    browser = await zendriver.start(headless=True)
    try:
        yield browser
    finally:
        await browser.stop()
