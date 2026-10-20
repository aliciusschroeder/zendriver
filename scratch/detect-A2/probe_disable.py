import asyncio, threading, http.server
import zendriver as zd
from zendriver import cdp

class H(http.server.BaseHTTPRequestHandler):
    def log_message(self, *a): pass
    def do_GET(self):
        body = b"<html>hi</html>"
        self.send_response(200); self.send_header("Content-Type", "text/html"); self.send_header("Content-Length", str(len(body))); self.end_headers(); self.wfile.write(body)

async def main():
    srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), H)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    base = f"http://127.0.0.1:{srv.server_address[1]}"
    browser = await zd.start(headless=True)
    try:
        tab = await browser.get(base + "/a")
        sent = []
        orig = tab._send_transaction
        async def spy(tx):
            sent.append((tx.method, tx.params)); return await orig(tx)
        tab._send_transaction = spy
        paused = []
        async def on_paused(e: cdp.fetch.RequestPaused):
            paused.append(e.request.url)   # only cares about one URL; never continues others
        tab.add_handler(cdp.fetch.RequestPaused, on_paused)
        await tab.send(cdp.fetch.enable(patterns=[cdp.fetch.RequestPattern(url_pattern="*/never-requested")]))
        await tab.send(cdp.fetch.disable())          # user stops intercepting
        print("after disable: enabled", tab.enabled_domains, "manual", tab.manually_enabled_domains)
        sent.clear()
        try:
            await asyncio.wait_for(tab.send(cdp.page.navigate(base + "/b")), 5)
            await asyncio.sleep(2)
            r = await asyncio.wait_for(tab.evaluate("location.href + ' ' + document.readyState"), 5)
            print("page:", r)
        except asyncio.TimeoutError:
            print("TIMEOUT")
        print("sent after disable:", sent[:4])
        print("paused requests:", paused)
    finally:
        await browser.stop()

asyncio.run(asyncio.wait_for(main(), 50))
