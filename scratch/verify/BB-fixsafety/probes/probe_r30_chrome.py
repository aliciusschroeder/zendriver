import asyncio
import http.server
import threading

import zendriver as zd
from zendriver import cdp

print("ZENDRIVER IMPORTED FROM", zd.__file__)

PAGES = {
    "/poll.html": b"<html><body>poll<script>setInterval(()=>fetch('/poll?'+Date.now()),300)</script></body></html>",
    "/broken.html": b"<html><body>broken<script>setTimeout(()=>fetch('/api.json').then(r=>r.text()).catch(e=>document.title='err:'+e),300)</script></body></html>",
    "/refused.html": b"<html><body>refused<script>setTimeout(()=>fetch('http://127.0.0.1:1/x').catch(e=>document.title='err:'+e),300)</script></body></html>",
}


class H(http.server.BaseHTTPRequestHandler):
    def log_message(self, *a: object) -> None:
        pass

    def do_GET(self) -> None:
        path = self.path.split("?")[0]
        if path == "/api.json":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", "1000")
            self.end_headers()
            self.wfile.write(b'{"a": 1234}')
            self.wfile.flush()
            self.close_connection = True
            return
        if path == "/poll":
            body = b"ok"
        else:
            body = PAGES.get(path, b"")
        self.send_response(200 if body else 404)
        self.send_header("Content-Type", "text/html")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


async def attempt(label: str, aw: object, t: float) -> None:
    try:
        res = await asyncio.wait_for(asyncio.shield(aw), t)  # type: ignore[arg-type]
        print(f"{label}: resolved -> {str(res)[:80]}")
    except asyncio.TimeoutError:
        print(f"{label}: still pending after {t}s")
    except Exception as e:
        print(f"{label}: raised {type(e).__name__}: {str(e).splitlines()[0]}")


async def main() -> None:
    httpd = http.server.ThreadingHTTPServer(("127.0.0.1", 0), H)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    base = f"http://127.0.0.1:{httpd.server_address[1]}"
    browser = await zd.start(headless=True)
    try:
        # A10.7: page initiated request on a tab where Network was never enabled
        tab = await browser.get(f"{base}/poll.html", new_tab=True)
        print("A10.7 enabled before:", tab.enabled_domains, tab.manually_enabled_domains)
        async with tab.expect_request(r".*/poll\?.*") as r:
            await attempt("A10.7 expect_request(self-polling page).value", r.value, 4)
        await tab.close()

        # A10.8 / B13.7: response headers then connection closed early
        tab = await browser.get("about:blank", new_tab=True)
        failed: list[str] = []
        tab.add_handler(
            cdp.network.LoadingFailed, lambda e: failed.append(e.error_text)
        )
        async with tab.expect_response(r".*/api\.json") as r2:
            await tab.get(f"{base}/broken.html")
            await attempt("A10.8 expect_response.value", r2.value, 5)
            await attempt("A10.8 expect_response.response_body", r2.response_body, 6)
        print("LoadingFailed seen:", failed)
        await tab.close()

        # B13.7: request fails before any response (connection refused)
        tab = await browser.get("about:blank", new_tab=True)
        async with tab.expect_response(r".*127\.0\.0\.1:1/x") as r3:
            await tab.get(f"{base}/refused.html")
            await attempt("B13.7 refused: expect_response.value", r3.value, 5)
            print("B13.7 request_future done:", r3.request_future.done())
        await tab.close()
    finally:
        await browser.stop()
        httpd.shutdown()


asyncio.run(main())
