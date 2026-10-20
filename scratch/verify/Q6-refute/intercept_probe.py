"""Side check: BaseFetchInterception / DownloadExpectation lost InvalidStateError on a burst."""

import asyncio
import gc
import http.server
import sys
import threading

sys.path.insert(0, "/tmp/claude-0/-home-user-zendriver/b2021b39-94e6-5220-9e66-7f33c0314a80/scratchpad/verify/Q6-refute")
import real_probe  # noqa: E402

import zendriver  # noqa: E402
from zendriver.cdp.fetch import RequestStage  # noqa: E402
from zendriver.cdp.network import ResourceType  # noqa: E402


async def main() -> None:
    srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), real_probe.H)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    base = f"http://127.0.0.1:{srv.server_address[1]}"
    errors = []
    asyncio.get_running_loop().set_exception_handler(lambda l, c: errors.append(repr(c.get("exception"))))
    browser = await zendriver.start(headless=True)
    try:
        tab = browser.main_tab
        for t in range(3):
            async with tab.intercept("*img*", RequestStage.REQUEST, ResourceType.IMAGE) as icpt:
                nav = asyncio.create_task(tab.get(f"{base}/imgs8.html?n={t:06d}"))
                req = await asyncio.wait_for(icpt.request, 10)
                print("intercepted", req.url.rsplit("/", 1)[-1])
                await icpt.continue_request()
                await asyncio.sleep(1.0)
            await asyncio.wait_for(nav, 20)
    finally:
        await browser.stop()
        srv.shutdown()
    gc.collect()
    await asyncio.sleep(0.05)
    gc.collect()
    print(sys.version.split()[0], "lost task errors:", len(errors), errors[:2])


asyncio.run(main())
