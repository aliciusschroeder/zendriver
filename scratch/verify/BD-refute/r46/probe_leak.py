import asyncio, sys, pathlib, time
import zendriver as zd
from zendriver import cdp
print("zendriver from", zd.__file__, sys.version.split()[0])
HERE = pathlib.Path(__file__).parent

async def heap(tab):
    await tab.send(cdp.heap_profiler.collect_garbage())
    return (await tab.send(cdp.runtime.get_heap_usage()))[0] / 1e6

async def loop(tab, n, use_apply):
    for i in range(n):
        await tab.evaluate("mk()")
        doc = await tab.send(cdp.dom.get_document(-1, True))
        nid = await tab.send(cdp.dom.query_selector(doc.node_id, "#box"))
        node = await tab.send(cdp.dom.describe_node(node_id=nid))
        from zendriver.core.element import Element
        el = Element(node, tab)
        if use_apply:
            await el.apply("(e) => e.id")

async def main():
    browser = await zd.start(headless=True)
    try:
        tab = await browser.get((HERE / "leak.html").as_uri())
        await tab.sleep(0.3)
        h0 = await heap(tab)
        t = time.monotonic(); await loop(tab, 300, False); h1 = await heap(tab)
        print(f"control 300 iters (no apply): heap {h0:.2f} -> {h1:.2f} MB  ({time.monotonic()-t:.1f}s)")
        t = time.monotonic(); await loop(tab, 300, True); h2 = await heap(tab)
        print(f"with apply 300 iters: heap {h1:.2f} -> {h2:.2f} MB  ({time.monotonic()-t:.1f}s)")
        await tab.send(cdp.runtime.release_object_group("console"))
        await tab.reload(); await tab.sleep(0.5)
        print("after reload heap", await heap(tab))
    finally:
        await browser.stop()
asyncio.run(main())
