import asyncio
import http.server
import sys
import threading

import zendriver as zd

print("zendriver from", zd.__file__)
SEEN = []


class H(http.server.BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def do_GET(self):
        SEEN.append((self.path, "HeadlessChrome" in self.headers.get("User-Agent", "")))
        if self.path.startswith("/opener"):
            body = b"<html><body><a id=a target=_blank href='/popup'>x</a></body></html>"
        else:
            body = b"<html><body>p</body></html>"
        self.send_response(200)
        self.send_header("Content-Type", "text/html")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


async def main():
    srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), H)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    B = f"http://127.0.0.1:{srv.server_address[1]}"
    browser = await zd.start(headless=True)
    try:
        tab = await asyncio.wait_for(browser.get(B + "/opener"), 20)
        await tab.evaluate("window.open('/popup-js'); 1")
        a = await tab.select("#a")
        await a.click()
        await asyncio.sleep(1.5)
        for p, h in SEEN:
            if not p.startswith("/favicon"):
                print(f"{p:10s} HeadlessChrome={h}")
    finally:
        await browser.stop()
        srv.shutdown()


asyncio.run(main())
