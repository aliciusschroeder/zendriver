import asyncio, sys, pathlib, time, psutil
import zendriver as zd
from zendriver import cdp
from zendriver.core.element import Element
print("zendriver from", zd.__file__, sys.version.split()[0])
HERE = pathlib.Path(__file__).parent

def renderer_rss(pid):
    tot = 0
    for c in psutil.Process(pid).children(recursive=True):
        try:
            if "--type=renderer" in " ".join(c.cmdline()):
                tot += c.memory_full_info().uss
        except psutil.Error: pass
    return tot / 1e6

async def gc(tab):
    for _ in range(3):
        await tab.send(cdp.heap_profiler.collect_garbage()); await asyncio.sleep(0.3)

async def loop(tab, n, use_apply):
    for i in range(n):
        await tab.evaluate("mk()")
        doc = await tab.send(cdp.dom.get_document(-1, True))
        nid = await tab.send(cdp.dom.query_selector(doc.node_id, "#box"))
        node = await tab.send(cdp.dom.describe_node(node_id=nid))
        el = Element(node, tab)
        if use_apply:
            await el.apply("(e) => e.id")

async def main():
    browser = await zd.start(headless=True)
    pid = browser._process_pid
    try:
        tab = await browser.get((HERE / "leak.html").as_uri())
        await tab.sleep(0.3)
        await gc(tab); r0 = renderer_rss(pid); print(f"renderer USS start {r0:.0f} MB")
        await loop(tab, 400, False); await gc(tab); r1 = renderer_rss(pid); print(f"after control 400 (no apply): {r1:.0f} MB")
        await loop(tab, 400, True); await gc(tab); r2 = renderer_rss(pid); print(f"after 400 apply on fresh 200KB nodes: {r2:.0f} MB")
        await tab.reload(); await tab.sleep(1); await gc(tab); r3 = renderer_rss(pid); print(f"after reload: {r3:.0f} MB")
    finally:
        await browser.stop()
asyncio.run(main())
