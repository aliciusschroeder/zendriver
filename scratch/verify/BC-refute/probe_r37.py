import asyncio
import sys

sys.path.insert(0, "/tmp/claude-0/-home-user-zendriver/b2021b39-94e6-5220-9e66-7f33c0314a80/scratchpad/verify/BC-refute")
import zendriver as zd
from zendriver import cdp
from zendriver.core.connection import ProtocolException
from helper import PAGES, serve, show, desc

print("zendriver from", zd.__file__, "python", sys.version.split()[0])

rows = "".join(f"<tr id='r{i}'><td>c{i}</td></tr>" for i in range(20))
PAGES["/main"] = f"""<html><body><p id="topp">top paragraph</p><p>two</p>
<table>{rows}</table></body></html>"""
PAGES["/reload"] = """<html><body><div id="top">top</div><iframe id="fr" src="/rinner"></iframe></body></html>"""
PAGES["/rinner"] = """<html><body><div id="inner">inner</div><script>setTimeout(()=>location.reload(), 20)</script></body></html>"""


async def main():
    srv, port = serve()
    browser = await zd.start(headless=True)
    try:
        base = f"http://127.0.0.1:{port}"
        tab = await browser.get(base + "/main")
        await tab.sleep(1.0)

        print("=== Chrome: does a second DOM.getDocument invalidate node ids from the first?")
        d1 = await tab.send(cdp.dom.get_document(-1, True))
        await tab.send(cdp.dom.query_selector(d1.node_id, "p"))
        print("   query on d1 before 2nd getDocument OK")
        d2 = await tab.send(cdp.dom.get_document(-1, True))
        try:
            await tab.send(cdp.dom.query_selector(d1.node_id, "p"))
            print("   query on d1 after 2nd getDocument: OK (ids", d1.node_id, d2.node_id, ")")
        except ProtocolException as e:
            print("   query on d1 after 2nd getDocument FAILS:", e.message.splitlines()[0], "ids", d1.node_id, d2.node_id)
        d3 = await tab.send(cdp.dom.get_document(-1, False))
        try:
            await tab.send(cdp.dom.query_selector(d2.node_id, "p"))
            print("   after shallow getDocument, d2 OK")
        except ProtocolException as e:
            print("   after shallow getDocument, d2 FAILS:", e.message.splitlines()[0])

        print("\n=== sequential controls")
        trs = await tab.select_all("tr")
        seq = [await r.query_selector("td") for r in trs]
        print("   sequential row.query_selector None count:", sum(x is None for x in seq), "of", len(seq))

        for attempt in range(3):
            trs = await tab.select_all("tr")
            res = await asyncio.gather(*(r.query_selector("td") for r in trs))
            left = sum(1 for r in trs if getattr(r, "__last", None))
            print(f"   [{attempt}] gather row.query_selector None count: {sum(x is None for x in res)} of {len(res)}; __last leftovers: {left}")
        trs = await tab.select_all("tr")
        res = await asyncio.gather(*(r.query_selector_all("td") for r in trs))
        print("   gather row.query_selector_all empty:", sum(not x for x in res))
        res = await asyncio.gather(*(tab.query_selector("#topp") for _ in range(10)))
        print("   gather 10x tab.query_selector None:", sum(x is None for x in res))
        res = await asyncio.gather(*(tab.query_selector_all("p") for _ in range(10)))
        print("   gather 10x tab.query_selector_all lens:", [len(x) for x in res])
        res = await asyncio.gather(*(tab.select("#topp", timeout=3) for _ in range(10)), return_exceptions=True)
        print("   gather 10x tab.select (retrying API):", [type(x).__name__ for x in res])
        res = await asyncio.gather(tab.query_selector("#topp"), tab.query_selector("#r3"))
        print("   gather 2x query_selector:", [desc(x) for x in res])
        res = await asyncio.gather(tab.find("top paragraph", timeout=3), tab.find("c7", timeout=3), return_exceptions=True)
        print("   gather 2x find:", [desc(x) if not isinstance(x, Exception) else repr(x) for x in res])

        print("\n=== __last leftover then sequential use")
        trs = await tab.select_all("tr")
        res = await asyncio.gather(*(r.query_selector("td") for r in trs))
        leftovers = [r for r in trs if getattr(r, "__last", None)]
        print("   leftovers:", len(leftovers))
        if leftovers:
            r = leftovers[0]
            # force a stale node id sequentially: another getDocument, then use the element directly through tab API
            await tab.send(cdp.dom.get_document(-1, True))
            out = await tab.query_selector("td", r)
            print("   sequential tab.query_selector('td', leftover) after a stale id:", desc(out))
            out = await r.query_selector("td")
            print("   leftover r.query_selector('td') (public API):", desc(out))

        print("\n=== A5.6 sequential trigger: iframe that reloads constantly")
        tab = await browser.get(base + "/reload")
        await tab.sleep(1.0)
        lens = []
        for _ in range(30):
            r = await tab.select_all("div", include_frames=True, timeout=2)
            lens.append(len(r))
        print("   sequential select_all lens with reloading iframe:", lens)
    finally:
        await browser.stop()
        srv.shutdown()


asyncio.run(asyncio.wait_for(main(), 110))
