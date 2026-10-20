import asyncio
import sys
import traceback

sys.path.insert(0, "/tmp/claude-0/-home-user-zendriver/b2021b39-94e6-5220-9e66-7f33c0314a80/scratchpad/detect-A5")
from server import start_server  # noqa

import zendriver as zd


async def step(name, coro, t=20):
    try:
        r = await asyncio.wait_for(coro, t)
        print(f"[{name}] ->", r)
        return r
    except BaseException as e:
        print(f"[{name}] EXC {type(e).__name__}: {e!s:.200}")
        return None


async def main():
    server, base = start_server()
    browser = await zd.start(headless=True)
    try:
        tab = await browser.get(base + "/")
        await tab.select("#topp")
        await asyncio.sleep(1.5)

        # H1 xpath timeout=0
        await step("xpath default", tab.xpath("//p[@id='topp']"))
        await step("xpath timeout=0", tab.xpath("//p[@id='topp']", timeout=0))
        await step("xpath timeout=0.001", tab.xpath("//p[@id='topp']", timeout=0.001))

        # H2 cross-origin iframe element query_selector
        cross = await tab.select("#cross-frame")
        print("cross content_document:", cross.content_document)
        await step("cross.query_selector_all", cross.query_selector_all("p"))
        await step("cross.query_selector", cross.query_selector("p"))

        # H3 same-origin iframe element
        same = await tab.select("#same-frame")
        await step("same.query_selector", same.query_selector("span"))
        inner = await step("select inner include_frames", tab.select("#inner", include_frames=True))
        if inner is not None:
            print("inner.parent:", await step("parent", asyncio.sleep(0, inner.parent)))
            await step("inner.query_selector_all b", inner.query_selector_all("b"))
            await step("inner.query_selector b", inner.query_selector("b"))
            await step("inner.children", asyncio.sleep(0, inner.children))
        spans = await step("select_all span include_frames", tab.select_all("span", include_frames=True))
        if spans:
            print("span parent:", spans[0].parent)

        # H5 find_all duplicates same-origin iframe text
        r = await step("find_all same origin text", tab.find_all("hello same origin", timeout=2))
        if r:
            print("backend ids:", [e.backend_node_id for e in r])
        r = await step("find_all top text", tab.find_all("top paragraph", timeout=2))

        # H6 invalid selector swallowed on element
        top = await tab.select("#top")
        await step("tab.query_selector_all invalid", tab.query_selector_all("a[["))
        await step("elem.query_selector_all invalid", top.query_selector_all("a[["))
        await step("elem.query_selector invalid", top.query_selector("a[["))
        await step("tab.query_selector invalid", tab.query_selector("a[["))

        # H7 return_enclosing_element
        r = await step("find return_enclosing False", tab.find("top paragraph", return_enclosing_element=False, timeout=2))
        if r is not None:
            print("node_type", r.node_type, r.node_name)
    finally:
        await browser.stop()
        server.shutdown()


asyncio.run(main())
