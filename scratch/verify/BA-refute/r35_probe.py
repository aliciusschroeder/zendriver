import asyncio, time, sys, threading, http.server, socketserver
import zendriver as zd
from zendriver import cdp
print("zendriver from", zd.__file__, sys.version.split()[0])
log = []
class H(http.server.BaseHTTPRequestHandler):
    def log_message(self, *a): pass
    def do_GET(self):
        ua = self.headers.get("User-Agent", "")
        chua = self.headers.get("Sec-CH-UA", "")
        log.append((self.path, "HeadlessChrome" in ua, "Headless" in chua, self.headers.get("Sec-Fetch-Dest")))
        if self.path.startswith("/beacon"):
            body = b""
            self.send_response(204); self.end_headers(); return
        body = (b"<title>t</title><script>new Image().src='/beacon?from=" + self.path.encode() +
                b"&jsua='+encodeURIComponent(navigator.userAgent.includes('Headless'))+'&wd='+navigator.webdriver;</script>"
                b"<a id=a href='/popup-link' target=_blank>x</a>")
        self.send_response(200); self.send_header("Content-Type","text/html"); self.send_header("Content-Length", str(len(body))); self.end_headers(); self.wfile.write(body)
class TS(socketserver.ThreadingMixIn, http.server.HTTPServer):
    daemon_threads = True
srv = TS(("127.0.0.1", 0), H)
threading.Thread(target=srv.serve_forever, daemon=True).start()
B = f"http://127.0.0.1:{srv.server_address[1]}"

async def main():
    b = await zd.start(headless=True)
    try:
        t0 = await b.get(B + "/main-tab")
        await asyncio.sleep(0.5)
        t1 = await b.get(B + "/new-tab", new_tab=True)
        await asyncio.sleep(0.5)
        t2 = await b.create_context(B + "/ctx")
        await asyncio.sleep(1.0)
        await t0.evaluate("void window.open('/popup-open')")
        await asyncio.sleep(1.0)
        await t1.reload()
        await asyncio.sleep(1.0)
        for e in log: print(e)
    finally:
        await b.stop()
        srv.shutdown()
asyncio.run(main())
