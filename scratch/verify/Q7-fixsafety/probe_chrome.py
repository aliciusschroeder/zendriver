import asyncio
import http.server
import threading
import traceback

import zendriver
from zendriver import cdp

print("zendriver imported from:", zendriver.__file__)


def start_http() -> tuple[http.server.ThreadingHTTPServer, str]:
    class H(http.server.BaseHTTPRequestHandler):
        def do_GET(self) -> None:
            body = b"<html><body>hi<img src='/pix.png'></body></html>"
            self.send_response(200)
            self.send_header("Content-Type", "text/html")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, *a: object) -> None:
            pass

    srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), H)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv, f"http://127.0.0.1:{srv.server_address[1]}/"


async def main() -> None:
    srv, url = start_http()
    browser = await zendriver.start(headless=True)
    try:
        tab = await browser.get(url)

        # scenario 1: public add/remove handler API
        def h(ev: object) -> None:
            pass

        tab.add_handler(cdp.network.RequestWillBeSent, h)
        await tab.evaluate("1")
        print("s1 enabled after first evaluate:", [m.__name__ for m in tab.enabled_domains])
        tab.remove_handlers(cdp.network.RequestWillBeSent, h)
        tab.add_handler(cdp.runtime.ConsoleAPICalled, h)
        try:
            r = await tab.evaluate("2")
            print("s1 second evaluate OK ->", r, [m.__name__ for m in tab.enabled_domains])
        except Exception as e:
            print("s1 second evaluate RAISED:", type(e).__name__, e)
        tab.remove_handlers()
        await tab.evaluate("3")  # converge: no handlers
        print("s1 converged:", [m.__name__ for m in tab.enabled_domains])

        # scenario 2: expect_request helper then a page handler then reload
        async with tab.expect_request(url) as req:
            await tab.reload()
            await asyncio.wait_for(req.value, 10)
        print("s2 enabled after expect_request:", [m.__name__ for m in tab.enabled_domains])
        loads: list[object] = []
        tab.add_handler(cdp.page.LoadEventFired, lambda ev: loads.append(ev))
        try:
            await tab.reload()
            print("s2 reload OK, enabled:", [m.__name__ for m in tab.enabled_domains])
        except Exception as e:
            print("s2 reload RAISED:", type(e).__name__, e)
            traceback.print_exc(limit=-4)
    finally:
        await browser.stop()
        srv.shutdown()


asyncio.run(asyncio.wait_for(main(), 90))
