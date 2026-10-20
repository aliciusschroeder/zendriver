import asyncio
import sys

sys.path.insert(0, "/tmp/claude-0/-home-user-zendriver/b2021b39-94e6-5220-9e66-7f33c0314a80/scratchpad/detect-A5")
from server import start_server  # noqa

import zendriver as zd


async def step(name, coro, t=30):
    try:
        r = await asyncio.wait_for(coro, t)
        print(f"[{name}] ->", r)
        return r
    except BaseException as e:
        print(f"[{name}] EXC {type(e).__name__}: {e!s:.300}")
        return None


async def main():
    server, base = start_server()
    browser = await zd.start(headless=True)
    try:
        tab = await browser.get(base + "/")
        await tab.select("#topp")
        await tab.select("#inner", include_frames=True)

        # find() on same-origin iframe text
        r = await step("find same-origin text", tab.find("hello same origin", timeout=2))
        if r is not None:
            print("  node_type", r.node_type, "node_name", r.node_name)
        r = await step("find best_match=False same-origin text", tab.find("hello same origin", best_match=False, timeout=2))
        if r is not None:
            print("  node_type", r.node_type, "node_name", r.node_name)

        # concurrent tab-level query_selector / query_selector_all
        res = await step("gather tab.query_selector x10", asyncio.gather(*(tab.query_selector("#topp") for _ in range(10))))
        if res is not None:
            print("  None count", sum(1 for x in res if x is None))
        res = await step("gather tab.query_selector_all x10", asyncio.gather(*(tab.query_selector_all("p") for _ in range(10))))
        if res is not None:
            print("  lens", [len(x) for x in res])
        res = await step("gather select_all div include_frames x6", asyncio.gather(*(tab.select_all("div", include_frames=True) for _ in range(6))))
        if res is not None:
            print("  lens", [len(x) for x in res])
        res = await step("sequential select_all div include_frames", tab.select_all("div", include_frames=True))
    finally:
        await browser.stop()
        server.shutdown()


asyncio.run(main())
