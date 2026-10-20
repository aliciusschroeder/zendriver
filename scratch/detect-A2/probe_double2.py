import asyncio, threading, http.server
import zendriver as zd
from zendriver import cdp

class H(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *a): pass
    def do_GET(self):
        body = b"<html>hi</html>" if self.path == "/" else b"ok"
        self.send_response(200); self.send_header("Content-Length", str(len(body))); self.end_headers(); self.wfile.write(body)

async def main():
    srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), H)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    base = f"http://127.0.0.1:{srv.server_address[1]}/"
    browser = await zd.start(headless=True)
    try:
        tab = await browser.get(base)
        await tab.send(cdp.runtime.evaluate("""
          window.pending = 0;
          window.iv = setInterval(() => { pending++; fetch('/other?' + Math.random()).finally(() => pending--); }, 2);
        """))
        await asyncio.sleep(0.3)
        paused = []
        tab.add_handler(cdp.fetch.RequestPaused, lambda e: paused.append((e.request.url, e.response_status_code)))
        await tab.send(cdp.fetch.enable(patterns=[cdp.fetch.RequestPattern(
            url_pattern="*/only-this.json", request_stage=cdp.fetch.RequestStage.RESPONSE)]))
        await asyncio.sleep(1)
        await tab.send(cdp.runtime.evaluate("clearInterval(window.iv)"))
        await asyncio.sleep(2)
        r = await tab.send(cdp.runtime.evaluate("window.pending", return_by_value=True))
        print("requests still pending 2s after stopping:", r[0].value)
        print("RequestPaused events for non-matching URLs:", len(paused), paused[:3])
    finally:
        await browser.stop()

asyncio.run(asyncio.wait_for(main(), 50))
