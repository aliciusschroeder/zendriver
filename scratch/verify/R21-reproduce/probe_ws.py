import asyncio, os, sys, json, threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
for k in ["no_proxy", "NO_PROXY", "http_proxy", "HTTP_PROXY", "https_proxy", "HTTPS_PROXY", "all_proxy", "ALL_PROXY"]:
    os.environ.pop(k, None)
log = []
class Proxy(BaseHTTPRequestHandler):
    def _deny(self):
        log.append(self.requestline); self.send_response(502); self.send_header("Content-Length", "0"); self.end_headers()
    do_GET = do_CONNECT = _deny
    def log_message(self, *a): pass
px = ThreadingHTTPServer(("127.0.0.1", 0), Proxy)
threading.Thread(target=px.serve_forever, daemon=True).start()
os.environ["http_proxy"] = f"http://127.0.0.1:{px.server_address[1]}"

import websockets, zendriver
from websockets.asyncio.server import serve
from zendriver.core.connection import Connection
from zendriver import cdp
print("websockets", websockets.__version__, websockets.__file__)
print("zendriver from", zendriver.__file__)

async def handler(ws):
    async for msg in ws:
        m = json.loads(msg)
        await ws.send(json.dumps({"id": m["id"], "result": {}}))

async def main():
    async with serve(handler, "127.0.0.1", 0) as srv:
        port = srv.sockets[0].getsockname()[1]
        conn = Connection(f"ws://127.0.0.1:{port}/devtools/browser/x")
        try:
            r = await asyncio.wait_for(conn.send(cdp.page.enable()), 15)
            print("CDP send OK", r)
        except Exception as e:
            print("CDP send FAILED", type(e).__name__, e)
        finally:
            try:
                await asyncio.wait_for(conn.aclose(), 5)
            except Exception as e:
                print("aclose:", type(e).__name__, e)
    print("proxy saw:", log)
asyncio.run(main())
px.shutdown()
