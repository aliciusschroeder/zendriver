"""R35 probe: user agent of the first document request of new tabs in headless mode."""

import asyncio
import http.server
import sys
import threading

import zendriver as zd

print("zendriver from", zd.__file__, "python", sys.version.split()[0])

UAS: list[tuple[str, str]] = []


class H(http.server.BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def do_GET(self):
        UAS.append((self.path, self.headers.get("User-Agent", "")))
        if self.path.startswith("/opener"):
            body = b"<html><body><a id=a target=_blank href='/popup'>x</a></body></html>"
        else:
            body = b"<html><title>p</title><script>document.title=navigator.userAgent</script></html>"
        self.send_response(200)
        self.send_header("Content-Type", "text/html")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


async def main():
    srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), H)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    B = f"http://127.0.0.1:{srv.server_address[1]}"
    browser = await zd.start(headless=True, expert="--expert" in sys.argv)
    try:
        await asyncio.wait_for(browser.get(B + "/main-tab"), 20)
        t2 = await asyncio.wait_for(browser.get(B + "/new-tab", new_tab=True), 20)
        await t2.sleep(0.5)
        print("new-tab document.title (JS-seen UA):", "Headless" in (await t2.evaluate("document.title")))
        t3 = await asyncio.wait_for(browser.create_context(B + "/context"), 20)
        await t3.sleep(0.5)
        print("context document.title (JS-seen UA):", "Headless" in (await t3.evaluate("document.title")))
        await t2.reload()
        await t2.sleep(0.5)
        for path, ua in UAS:
            print(f"{path:12s} HeadlessChrome={'HeadlessChrome' in ua}")
    finally:
        await browser.stop()
        srv.shutdown()


asyncio.run(main())
