import asyncio
import sys

sys.path.insert(0, "/tmp/claude-0/-home-user-zendriver/b2021b39-94e6-5220-9e66-7f33c0314a80/scratchpad/verify/Q6-refute")
import real_probe  # noqa: E402
import http.server, threading  # noqa: E401,E402

import zendriver  # noqa: E402
from zendriver import cdp  # noqa: E402


async def main() -> None:
    srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), real_probe.H)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    base = f"http://127.0.0.1:{srv.server_address[1]}"
    browser = await zendriver.start(headless=True)
    try:
        tab = browser.main_tab
        log = []
        tab.add_handler(cdp.network.RequestWillBeSent, lambda e: log.append(("RWBS", e.request_id, e.request.url[-30:])))
        tab.add_handler(cdp.network.ResponseReceived, lambda e: log.append(("RR", e.request_id, e.response.url[-30:])))
        tab.add_handler(cdp.network.LoadingFinished, lambda e: log.append(("LF", e.request_id)))
        tab.add_handler(cdp.network.LoadingFailed, lambda e: log.append(("LFAIL", e.request_id, e.error_text)))
        async with tab.expect_request(r".*/a\.json.*") as exp:
            await tab.get(f"{base}/single.html?n=1")
            await asyncio.sleep(2)
            print("request_future done", exp.request_future.done(), "resp", exp.response_future.done(), "lf", exp.loading_finished_future.done(), "exp.request_id", exp.request_id)
            print("handlers LF:", tab.handlers[cdp.network.LoadingFinished])
        for l in log:
            print(l)
    finally:
        await browser.stop()
        srv.shutdown()


asyncio.run(main())
