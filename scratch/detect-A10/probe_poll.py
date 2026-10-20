import asyncio, threading, http.server, os, sys
import zendriver as zd
class H(http.server.BaseHTTPRequestHandler):
    def log_message(self, *a): pass
    def do_GET(self):
        if self.path.startswith("/page"):
            b = b"<html><body><script>setInterval(()=>fetch('/poll?'+Date.now()), 300);</script></body></html>"; ct="text/html"
        else:
            b = b"{}"; ct = "application/json"
        self.send_response(200); self.send_header("Content-Type", ct); self.send_header("Content-Length", str(len(b))); self.end_headers(); self.wfile.write(b)
srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), H)
port = srv.server_address[1]
threading.Thread(target=srv.serve_forever, daemon=True).start()
BASE = f"http://127.0.0.1:{port}"
async def main():
    browser = await zd.start(headless=True, browser_connection_timeout=1.0, browser_connection_max_tries=30)
    tab = browser.main_tab
    await tab.get(BASE + "/page")
    await asyncio.sleep(1)
    print("enabled domains before:", [d.__name__ for d in tab.enabled_domains], [d.__name__ for d in tab.manually_enabled_domains])
    async with tab.expect_request(r".*/poll.*") as r:
        try:
            v = await asyncio.wait_for(asyncio.shield(r.value), 5)
            print("got", v.request.url)
        except asyncio.TimeoutError:
            print("expect_request on a self-polling page: nothing after 5s (Network domain not enabled)")
        await tab.evaluate("1")   # any send -> _register_handlers enables Network
        v = await asyncio.wait_for(asyncio.shield(r.value), 5)
        print("after an unrelated tab.send:", v.request.url.split('?')[0])
    await browser.stop()
asyncio.run(main())
