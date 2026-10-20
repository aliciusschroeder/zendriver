import asyncio
import sys

sys.path.insert(0, "/tmp/claude-0/-home-user-zendriver/b2021b39-94e6-5220-9e66-7f33c0314a80/scratchpad/detect-A5")
from server import start_server  # noqa

import zendriver as zd


async def main():
    server, base = start_server()
    browser = await zd.start(headless=True)
    try:
        tab = await browser.get(base + "/")
        p_tab = await tab.select("#topp")
        print("tab-level p.parent:", p_tab.parent)
        container = await tab.select("#top")
        p = await container.query_selector("p")
        print("elem-level p:", p, "type(p.node):", type(p.node).__name__, "tree type:", type(p.tree).__name__)
        print("elem-level p.parent:", p.parent)
        ps = await container.query_selector_all("p")
        print("elem-level qsa p.parent:", ps[0].parent)
        # iframe element query on same-origin iframe
        same = await tab.select("#same-frame")
        span = await same.query_selector("span")
        print("iframe-scoped span.parent:", span.parent)
    finally:
        await browser.stop()
        server.shutdown()


asyncio.run(main())
