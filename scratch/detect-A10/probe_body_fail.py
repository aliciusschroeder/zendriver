import asyncio, threading, http.server, os, sys
import zendriver as zd
class H(http.server.BaseHTTPRequestHandler):
    def log_message(self, *a): pass
    def do_GET(self):
        if self.path.startswith("/page"):
            b = b"<html><body><script>fetch('/api.json').then(r=>r.text()).catch(e=>window.__err=String(e));</script></body></html>"
            self.send_response(200); self.send_header("Content-Type", "text/html"); self.send_header("Content-Length", str(len(b))); self.end_headers(); self.wfile.write(b)
        else:
            self.send_response(200); self.send_header("Content-Type", "application/json"); self.send_header("Content-Length", "1000"); self.end_headers()
            self.wfile.write(b'{"partial":'); self.wfile.flush()
            self.close_connection = True
srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), H)
port = srv.server_address[1]
threading.Thread(target=srv.serve_forever, daemon=True).start()
BASE = f"http://127.0.0.1:{port}"
async def main():
    browser = await zd.start(headless=True, browser_connection_timeout=1.0, browser_connection_max_tries=30)
    tab = browser.main_tab
    failed = []
    tab.add_handler(zd.cdp.network.LoadingFailed, lambda e: failed.append(e.error_text))
    async with tab.expect_response(r".*/api\.json") as r:
        await tab.get(BASE + "/page")
        resp = await asyncio.wait_for(asyncio.shield(r.value), 5)
        print("response received:", resp.response.status)
        try:
            body = await asyncio.wait_for(asyncio.shield(r.response_body), 10)
            print("body:", body)
        except asyncio.TimeoutError:
            print("response_body still pending after 10s; LoadingFailed events seen:", failed, "page err:", await tab.evaluate("window.__err"))
    await browser.stop()
asyncio.run(main())
