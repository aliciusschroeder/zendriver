"""Real-Chromium probe for Q11 review: default wait on a complete page, and
the navigation-in-flight behaviour change."""

import asyncio
import http.server
import sys
import threading
import time

import zendriver as zd


class Handler(http.server.BaseHTTPRequestHandler):
    def log_message(self, *a):  # quiet
        pass

    def do_GET(self):
        if self.path.startswith("/slow"):
            # headers fast, body after 1.5s, so the old document stays current
            time.sleep(1.5)
        body = b"<html><body><a id=l href='/slow'>x</a><p>hi</p></body></html>"
        self.send_response(200)
        self.send_header("Content-Type", "text/html")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


async def timed(label, coro):
    t = time.monotonic()
    try:
        r = await asyncio.wait_for(coro, 30)
        print(f"[{label}] OK {r!r} in {time.monotonic() - t:.2f}s")
    except BaseException as e:
        print(f"[{label}] EXC {type(e).__name__}: {e} in {time.monotonic() - t:.2f}s")


async def main():
    print("zendriver from", zd.__file__, sys.version.split()[0])
    srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    base = f"http://127.0.0.1:{srv.server_address[1]}"
    browser = await zd.start(headless=True)
    try:
        tab = await browser.get(base + "/fast")
        print("readyState after get:", await tab.evaluate("document.readyState"))
        await timed("default on complete", tab.wait_for_ready_state(timeout=3))
        await timed("loading on complete", tab.wait_for_ready_state("loading", timeout=3))
        await timed("complete on complete", tab.wait_for_ready_state("complete", timeout=3))

        # navigation in flight: trigger a slow navigation, then wait at once
        await tab.evaluate("document.getElementById('l').click()")
        await timed("default during nav", tab.wait_for_ready_state(timeout=5))
        print("url right after:", await tab.evaluate("location.pathname"))
        await asyncio.sleep(2.5)
        print("url later:", await tab.evaluate("location.pathname"))
    finally:
        await browser.stop()
        srv.shutdown()


asyncio.run(main())
