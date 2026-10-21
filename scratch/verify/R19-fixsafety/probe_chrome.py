"""Real-Chromium probe: documented sync RequestPaused handler using feed_cdp."""

import asyncio
import functools
import http.server
import sys
import tempfile
import threading

import zendriver
from zendriver import cdp

print("zendriver imported from:", zendriver.__file__, "python", sys.version.split()[0])


def serve() -> tuple[http.server.ThreadingHTTPServer, str]:
    d = tempfile.mkdtemp(dir=sys.argv[1])
    with open(f"{d}/index.html", "w") as f:
        f.write("<html><title>OK</title><body>hi</body></html>")
    with open(f"{d}/x", "w") as f:
        f.write("x")
    handler = functools.partial(
        http.server.SimpleHTTPRequestHandler, directory=d
    )
    handler.log_message = lambda *a, **k: None  # type: ignore
    srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv, f"http://127.0.0.1:{srv.server_address[1]}"


async def main() -> None:
    srv, base = serve()
    browser = await zendriver.start(headless=True)
    try:
        tab = await browser.get(base + "/index.html")
        seen: list[str] = []

        def on_paused(ev: cdp.fetch.RequestPaused) -> None:
            seen.append(threading.current_thread().name)
            tab.feed_cdp(cdp.fetch.continue_request(request_id=ev.request_id))

        tab.add_handler(cdp.fetch.RequestPaused, on_paused)
        await tab.send(cdp.fetch.enable())
        try:
            res = await asyncio.wait_for(
                tab.send(
                    cdp.runtime.evaluate(
                        "fetch('/x').then(r => r.status)", await_promise=True
                    )
                ),
                8,
            )
            print("fetch completed, status =", res[0].value, "handler threads", seen)
        except asyncio.TimeoutError:
            print("page fetch HUNG: request stayed paused; handler threads", seen)
        await tab.send(cdp.fetch.disable())
    finally:
        await browser.stop()
        srv.shutdown()


asyncio.run(main())
