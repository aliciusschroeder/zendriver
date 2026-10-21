"""R17 probe: Browser.get on non-committing navigations, and orphan tab on new_tab timeout."""

import asyncio
import http.server
import sys
import threading
import time

import zendriver as zd
from zendriver import cdp

print("zendriver from", zd.__file__, "python", sys.version.split()[0])

UAS: list[tuple[str, str]] = []


class H(http.server.BaseHTTPRequestHandler):
    def log_message(self, *a):  # quiet
        pass

    def do_GET(self):
        UAS.append((self.path, self.headers.get("User-Agent", "")))
        if self.path.startswith("/204"):
            self.send_response(204)
            self.end_headers()
            return
        if self.path.startswith("/dl"):
            body = b"x" * 100
            self.send_response(200)
            self.send_header("Content-Type", "application/zip")
            self.send_header("Content-Disposition", "attachment; filename=f.zip")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        if self.path.startswith("/slow"):
            time.sleep(3)
        body = b"<html><title>p</title><body>hi</body></html>"
        self.send_response(200)
        self.send_header("Content-Type", "text/html")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


async def timed(label, coro):
    t = time.monotonic()
    try:
        r = await asyncio.wait_for(coro, 30)
        print(f"{label}: OK in {time.monotonic() - t:.2f}s -> {r!r}"[:200])
        return r
    except BaseException as e:
        print(f"{label}: {type(e).__name__} after {time.monotonic() - t:.2f}s {e}")
        return None


async def main():
    srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), H)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    B = f"http://127.0.0.1:{srv.server_address[1]}"
    browser = await zd.start(headless=True)
    try:
        await timed("browser.get(page)", browser.get(B + "/page", timeout=3))
        await timed("browser.get(204)", browser.get(B + "/204", timeout=3))
        await timed("browser.get(dl)", browser.get(B + "/dl", timeout=3))
        tab = browser.tabs[0]
        await timed("tab.get(204)", tab.get(B + "/204"))
        # what does Page.navigate say for 204 / dl?
        r = await tab.send(cdp.page.navigate(B + "/204"))
        print("raw navigate 204 ->", r)
        r = await tab.send(cdp.page.navigate(B + "/dl"))
        print("raw navigate dl ->", r)

        # orphan: new_tab with a slow page and a short timeout
        before = {t.target_id for t in await browser._get_targets() if t.type_ == "page"}
        await timed(
            "browser.get(slow, new_tab, timeout=0.5)",
            browser.get(B + "/slow", new_tab=True, timeout=0.5),
        )
        after = {t.target_id for t in await browser._get_targets() if t.type_ == "page"}
        print("page targets before", len(before), "after", len(after), "orphans", after - before)
        # new_tab to 204 also never commits
        before = after
        await timed(
            "browser.get(204, new_tab, timeout=2)",
            browser.get(B + "/204", new_tab=True, timeout=2),
        )
        after = {t.target_id for t in await browser._get_targets() if t.type_ == "page"}
        print("page targets before", len(before), "after", len(after), "orphans", after - before)
    finally:
        await browser.stop()
        srv.shutdown()


asyncio.run(main())
