"""Q11 refute probe: real headless Chromium, wait_for_ready_state semantics."""

import asyncio
import http.server
import os
import sys
import tempfile
import threading
import time

import zendriver

print("zendriver from", zendriver.__file__, "python", sys.version.split()[0])

SLOW_SECONDS = 4.0


class Handler(http.server.BaseHTTPRequestHandler):
    def log_message(self, *a):  # quiet
        pass

    def do_GET(self):
        if self.path.startswith("/slow.png"):
            time.sleep(SLOW_SECONDS)
            self.send_response(200)
            self.send_header("Content-Type", "image/png")
            self.send_header("Content-Length", "0")
            self.end_headers()
            return
        if self.path.startswith("/slowpage"):
            body = b"<html><body><p>hi</p><img src='/slow.png?x=%d'></body></html>" % int(
                time.time() * 1000
            )
        else:
            body = b"<html><body><p>fast</p></body></html>"
        self.send_response(200)
        self.send_header("Content-Type", "text/html")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


async def timed(label, coro):
    t0 = time.monotonic()
    try:
        r = await asyncio.wait_for(coro, 30)  # outer safety net
        print(f"[{label}] OK {r!r} in {time.monotonic() - t0:.2f}s")
    except BaseException as e:  # noqa
        print(f"[{label}] EXC {type(e).__name__}: {e} in {time.monotonic() - t0:.2f}s")


async def main():
    srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    port = srv.server_address[1]
    th = threading.Thread(target=srv.serve_forever, daemon=True)
    th.start()
    tmpdir = tempfile.mkdtemp(dir=os.path.dirname(os.path.abspath(__file__)))
    fpath = os.path.join(tmpdir, "fast.html")
    with open(fpath, "w") as f:
        f.write("<html><body><p>file page</p></body></html>")

    browser = await zendriver.start(headless=True)
    try:
        # 1. fast http page, immediately after browser.get (no sleep)
        tab = await browser.get(f"http://127.0.0.1:{port}/fast")
        rs = await tab.evaluate("document.readyState")
        print("fast http page readyState right after browser.get:", rs)
        await timed("default(interactive) fast http", tab.wait_for_ready_state(timeout=3))
        await timed("complete fast http", tab.wait_for_ready_state("complete", timeout=3))
        await timed("loading fast http", tab.wait_for_ready_state("loading", timeout=2))

        # 2. file:// page via tab.get (same tab)
        await tab.get("file://" + fpath)
        rs = await tab.evaluate("document.readyState")
        print("file page readyState right after tab.get:", rs)
        await timed("default(interactive) file page", tab.wait_for_ready_state(timeout=3))

        # 3. slow-subresource page: interactive phase lasts ~SLOW_SECONDS
        tab2 = await browser.get(f"http://127.0.0.1:{port}/slowpage", new_tab=True)
        rs = await tab2.evaluate("document.readyState")
        print("slow page readyState right after browser.get(new_tab):", rs)
        await timed("default(interactive) slow page", tab2.wait_for_ready_state(timeout=3))
        await timed("complete slow page", tab2.wait_for_ready_state("complete", timeout=10))
        await timed("default(interactive) slow page AFTER complete", tab2.wait_for_ready_state(timeout=3))

        # 4. Does readyState ever go backwards for one document? document.open()
        rs = await tab.evaluate(
            "(() => { const before = document.readyState; document.open(); const after = document.readyState; document.close(); return before + '->' + after + '->' + document.readyState; })()"
        )
        print("document.open() readyState transitions:", rs)

        # 5. readyState after history.pushState / hash navigation (same document)
        await tab.evaluate("history.pushState({}, '', '#x')")
        print("after pushState:", await tab.evaluate("document.readyState"))
    finally:
        await browser.stop()
        srv.shutdown()
        import shutil

        shutil.rmtree(tmpdir, ignore_errors=True)


asyncio.run(main())
