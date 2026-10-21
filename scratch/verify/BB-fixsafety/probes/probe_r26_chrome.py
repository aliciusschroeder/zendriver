import asyncio
import functools
import http.server
import os
import sys
import tempfile
import threading

import zendriver as zd
from zendriver import cdp

print("ZENDRIVER IMPORTED FROM", zd.__file__)


def serve(root: str) -> tuple[http.server.ThreadingHTTPServer, int]:
    handler = functools.partial(
        http.server.SimpleHTTPRequestHandler, directory=root
    )
    handler.log_message = lambda *a, **k: None  # type: ignore
    httpd = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    return httpd, httpd.server_address[1]


async def main() -> None:
    root = tempfile.mkdtemp(dir=os.path.dirname(__file__))
    for name in ("a", "b", "c", "d"):
        with open(os.path.join(root, f"{name}.html"), "w") as f:
            f.write(f"<html><body>{name}</body></html>")
    httpd, port = serve(root)
    base = f"http://127.0.0.1:{port}"
    browser = await zd.start(headless=True)
    try:
        tab = browser.main_tab
        assert tab is not None

        # --- A12.2: auto enabled Fetch is left on after its handler is removed
        async def cont(ev: cdp.fetch.RequestPaused) -> None:
            await tab.send(cdp.fetch.continue_request(request_id=ev.request_id))

        tab.add_handler(cdp.fetch.RequestPaused, cont)
        await asyncio.wait_for(tab.send(cdp.page.navigate(f"{base}/a.html")), 10)
        print("A12.2 with handler: navigate ok; enabled", tab.enabled_domains)
        tab.remove_handlers(cdp.fetch.RequestPaused, cont)
        try:
            await asyncio.wait_for(tab.send(cdp.page.navigate(f"{base}/b.html")), 6)
            print("A12.2 after remove: navigate OK")
        except asyncio.TimeoutError:
            print("A12.2 after remove: navigate TIMED OUT; enabled", tab.enabled_domains)
            # unblock the tab for the next probe
            await tab.send(cdp.fetch.disable())
            await asyncio.sleep(0.5)

        # --- A2.2: manual disable undone by a param-less enable
        seen: list[str] = []

        def ignore(ev: cdp.fetch.RequestPaused) -> None:
            seen.append(ev.request.url)

        tab.add_handler(cdp.fetch.RequestPaused, ignore)
        await tab.send(
            cdp.fetch.enable(patterns=[cdp.fetch.RequestPattern(url_pattern="*/never")])
        )
        await tab.send(cdp.fetch.disable())
        try:
            await asyncio.wait_for(tab.send(cdp.page.navigate(f"{base}/c.html")), 6)
            print("A2.2 after manual disable: navigate OK; paused", seen)
        except asyncio.TimeoutError:
            print("A2.2 after manual disable: navigate TIMED OUT; paused", seen)
        tab.remove_handlers(cdp.fetch.RequestPaused, ignore)
        try:
            await asyncio.wait_for(tab.send(cdp.fetch.disable()), 5)
        except Exception as e:
            print("cleanup fetch.disable:", e)
        await asyncio.sleep(0.5)

        # --- fix safety: does Network.disable drop buffered response bodies?
        finished: dict[str, cdp.network.RequestId] = {}

        def lf(ev: cdp.network.ResponseReceived) -> None:
            if ev.response.url.endswith("/d.html"):
                finished["id"] = ev.request_id

        tab.add_handler(cdp.network.ResponseReceived, lf)
        await tab.send(cdp.page.navigate(f"{base}/d.html"))
        for _ in range(50):
            if "id" in finished:
                break
            await asyncio.sleep(0.1)
        await asyncio.sleep(0.5)
        rid = finished["id"]
        body = await tab.send(cdp.network.get_response_body(rid), _is_update=True)
        print("body before Network.disable:", body)
        await tab.send(cdp.network.disable(), _is_update=True)
        try:
            body = await tab.send(cdp.network.get_response_body(rid), _is_update=True)
            print("body after Network.disable:", body)
        except Exception as e:
            print("body after Network.disable raised:", type(e).__name__, str(e).splitlines()[0])
        await tab.send(cdp.network.enable(), _is_update=True)
        try:
            body = await tab.send(cdp.network.get_response_body(rid), _is_update=True)
            print("body after re-enable:", body)
        except Exception as e:
            print("body after re-enable raised:", type(e).__name__, str(e).splitlines()[0])
    finally:
        await browser.stop()
        httpd.shutdown()
        import shutil

        shutil.rmtree(root, ignore_errors=True)


asyncio.run(main())
