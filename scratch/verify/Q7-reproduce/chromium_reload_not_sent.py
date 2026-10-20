"""Show that the failed tab.reload() never reaches Chromium (server hit counter)."""
import asyncio
import http.server
import sys
import threading

import zendriver
from zendriver import cdp

print("zendriver from:", zendriver.__file__, "python", sys.version.split()[0])
HITS = []


class H(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        HITS.append(self.path)
        body = b"<html><body>hello</body></html>"
        self.send_response(200)
        self.send_header("Content-Type", "text/html")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *a):
        pass


srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), H)
threading.Thread(target=srv.serve_forever, daemon=True).start()
URL = f"http://127.0.0.1:{srv.server_address[1]}/p"


async def main():
    browser = await zendriver.start(headless=True)
    try:
        tab = await browser.get(URL)
        async with tab.expect_request(URL) as req:
            await tab.reload()
            await asyncio.wait_for(req.request, 20)
        await asyncio.sleep(1)
        before = len([p for p in HITS if p == "/p"])
        loads = []
        tab.add_handler(cdp.page.LoadEventFired, lambda e: loads.append(e))
        try:
            await asyncio.wait_for(tab.reload(), 20)
            print("reload OK")
        except Exception as e:
            print("reload RAISED", type(e).__name__, e)
        await asyncio.sleep(2)
        after = len([p for p in HITS if p == "/p"])
        print(f"server hits for page before={before} after={after} LoadEventFired seen={len(loads)}")
        # a subsequent reload works and does reach the server
        await asyncio.wait_for(tab.reload(), 20)
        await asyncio.sleep(2)
        print(f"after a 2nd reload: hits={len([p for p in HITS if p == '/p'])} LoadEventFired seen={len(loads)}")
    finally:
        await browser.stop()
        srv.shutdown()


asyncio.run(main())
