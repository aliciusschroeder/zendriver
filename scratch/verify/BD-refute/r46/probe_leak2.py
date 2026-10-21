import asyncio, sys, pathlib, time
import zendriver as zd
from zendriver import cdp
from zendriver.core.element import Element
print("zendriver from", zd.__file__, sys.version.split()[0])
HERE = pathlib.Path(__file__).parent

async def heap(tab):
    await tab.send(cdp.heap_profiler.collect_garbage())
    await asyncio.sleep(0.5)
    await tab.send(cdp.heap_profiler.collect_garbage())
    r = await tab.send(cdp.runtime.get_heap_usage())
    return " ".join(f"{x/1e6:.1f}" for x in r)

async def loop(tab, n, use_apply):
    first = None
    for i in range(n):
        await tab.evaluate("mk()")
        doc = await tab.send(cdp.dom.get_document(-1, True))
        nid = await tab.send(cdp.dom.query_selector(doc.node_id, "#box"))
        node = await tab.send(cdp.dom.describe_node(node_id=nid))
        el = Element(node, tab)
        if use_apply:
            await el.apply("(e) => e.id")
            if first is None: first = el._remote_object.object_id
    return first

async def main():
    browser = await zd.start(headless=True)
    try:
        tab = await browser.get((HERE / "leak.html").as_uri())
        await tab.sleep(0.3)
        print("heap (used total embedder backing) MB:", await heap(tab))
        await loop(tab, 300, False); print("after control 300:", await heap(tab))
        first = await loop(tab, 300, True); print("after apply 300:", await heap(tab))
        r = await tab.send(cdp.runtime.call_function_on("function(){return [this.isConnected, this.textContent.length]}", object_id=first, return_by_value=True))
        print("first detached handle still alive:", r[0].value)
    finally:
        await browser.stop()
asyncio.run(main())
