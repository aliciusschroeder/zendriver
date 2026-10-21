"""Browser-free: does HTTPApi route loopback DevTools requests via http_proxy env?"""
import asyncio, json, os, sys, threading, socket
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import zendriver
from zendriver.core.browser import HTTPApi
print("zendriver from", zendriver.__file__, "python", sys.version.split()[0])

proxy_log = []
devtools_hits = []

class DevTools(BaseHTTPRequestHandler):
    def do_GET(self):
        devtools_hits.append(self.requestline)
        body = json.dumps({"Browser": "Fake/1", "webSocketDebuggerUrl": "ws://x"}).encode()
        self.send_response(200); self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body))); self.end_headers(); self.wfile.write(body)
    def log_message(self, *a): pass

class Proxy(BaseHTTPRequestHandler):
    def do_GET(self):
        proxy_log.append(self.requestline)
        self.send_response(502); self.send_header("Content-Length", "0"); self.end_headers()
    def log_message(self, *a): pass

def serve(handler):
    srv = ThreadingHTTPServer(("127.0.0.1", 0), handler)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv

async def attempt(label, env_updates, drop):
    saved = dict(os.environ)
    try:
        for k in drop: os.environ.pop(k, None)
        os.environ.update(env_updates)
        proxy_log.clear(); devtools_hits.clear()
        api = HTTPApi(("127.0.0.1", dt.server_address[1]))
        try:
            r = await asyncio.wait_for(api.get("version"), 15)
            res = f"OK {r}"
        except Exception as e:
            res = f"FAIL {type(e).__name__}: {e}"
        print(f"[{label}] result={res}\n   proxy saw={proxy_log}\n   devtools saw={devtools_hits}")
    finally:
        os.environ.clear(); os.environ.update(saved)

dt = serve(DevTools)
px = serve(Proxy)
purl = f"http://127.0.0.1:{px.server_address[1]}"
ALL = ["no_proxy", "NO_PROXY", "http_proxy", "HTTP_PROXY", "https_proxy", "HTTPS_PROXY", "all_proxy", "ALL_PROXY"]

async def main():
    await attempt("baseline: no proxy vars", {}, ALL)
    await attempt("http_proxy, no no_proxy", {"http_proxy": purl}, ALL)
    await attempt("HTTP_PROXY uppercase, no no_proxy", {"HTTP_PROXY": purl}, ALL)
    await attempt("https_proxy only (http url)", {"https_proxy": purl}, ALL)
    await attempt("http_proxy + no_proxy=127.0.0.1", {"http_proxy": purl, "no_proxy": "127.0.0.1"}, ALL)
    await attempt("http_proxy + no_proxy=localhost only", {"http_proxy": purl, "no_proxy": "localhost"}, ALL)

asyncio.run(main())
dt.shutdown(); px.shutdown()
