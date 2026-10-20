import asyncio
import sys

sys.path.insert(0, "/tmp/claude-0/-home-user-zendriver/b2021b39-94e6-5220-9e66-7f33c0314a80/scratchpad/detect-A5")
from server import start_server  # noqa

import zendriver as zd
from zendriver import cdp


async def main():
    server, base = start_server()
    browser = await zd.start(headless=True)
    try:
        tab = await browser.get(base + "/")
        inner = await tab.select("#inner", include_frames=True)
        id0 = inner.node_id
        await inner.update()
        print("node_id before/after update:", id0, inner.node_id)
        try:
            print(await tab.send(cdp.dom.query_selector_all(inner.node_id, "b")))
        except Exception as e:
            print("direct qsa after update:", str(e).splitlines()[0])
        # xpath timeout=0 vs element present; and how many CDP round trips xpath makes for a miss in 0.5s
        n = 0
        orig = tab.send

        async def counting_send(*a, **k):
            nonlocal n
            n += 1
            return await orig(*a, **k)

        tab.send = counting_send
        r = await tab.xpath("//nothing-here", timeout=0.5)
        print("xpath miss result", r, "sends in 0.5s:", n)
    finally:
        await browser.stop()
        server.shutdown()


asyncio.run(main())
