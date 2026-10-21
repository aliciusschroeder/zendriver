import asyncio
import io
import contextlib
import sys
import traceback

sys.path.insert(0, __file__.rsplit("/", 1)[0])
import zendriver as zd  # noqa: E402
from probe_common import serve  # noqa: E402

print("zendriver from", zd.__file__)


async def step(name, coro):
    try:
        r = await asyncio.wait_for(coro, 20)
        print(f"[{name}] ->", repr(r)[:200])
        return r
    except Exception as e:
        print(f"[{name}] EXC {type(e).__name__}: {e}"[:300])
        return None


async def main() -> None:
    srv, port = serve()
    browser = await zd.start(headless=True)
    try:
        tab = await browser.get(f"http://127.0.0.1:{port}/main")
        await tab.wait_for_ready_state("complete")
        await asyncio.sleep(1.0)
        # ---------------- R28 ----------------
        sd = await tab.select("#sd")
        inner = await sd.query_selector("#inner")
        print("R28 inner via iframe.query_selector:", inner, "parent:", inner.parent)
        await tab.evaluate(
            "document.getElementById('sd').contentDocument.getElementById('inner').setAttribute('data-v','2')"
        )
        await inner.update()
        print("R28 after update data-v:", inner.get("data-v"), "parent:", inner.parent)
        await inner.remove_from_dom()
        still = await tab.evaluate(
            "!!document.getElementById('sd').contentDocument.getElementById('inner')"
        )
        print("R28 inner still in iframe after remove_from_dom:", still)
        topp = await tab.select("#topp")
        await topp.remove_from_dom()
        print(
            "R28 control topp still present:",
            await tab.evaluate("!!document.getElementById('topp')"),
        )
        # A5.4
        finner = await tab.select("#inner", include_frames=True)
        print("A5.4 finner:", finner, "parent:", finner.parent)
        await step("A5.4 finner.query_selector_all b", finner.query_selector_all("b"))
        await step("A5.4 finner.query_selector b", finner.query_selector("b"))
        print("A5.4 finner.children:", finner.children)
        # A5.5a
        spans = await tab.select_all("span", include_frames=True)
        print("A5.5a span:", spans, "parent:", spans[0].parent if spans else None)
        # A5.9/A6.3
        r = await step("A5.9 find_all same-origin", tab.find_all("hello same origin"))
        if r:
            print("   types:", [(e.node_name, e.node_type, e.backend_node_id) for e in r])
        el = await step(
            "A5.9 find best_match=False",
            tab.find("hello same origin", best_match=False),
        )
        if el is not None:
            print("   node:", el.node_name, el.node_type)
        el = await step("A6.3 wait_for(text=inner needle)", tab.wait_for(text="inner needle"))
        if el is not None:
            print("   node:", el.node_name, el.node_type)
            await step("A6.3 click", el.click())
            await asyncio.sleep(0.3)
            print(
                "   clicked:",
                await tab.evaluate(
                    "document.getElementById('fr').contentWindow.clicked || null"
                ),
            )
        # ---------------- R29 ----------------
        await step("A6.2 find_elements_by_text needle", tab.find_elements_by_text("needle"))
        await step("A6.2 find shadow needle", tab.find("shadow needle", timeout=1))
        cross = await tab.select("#cross")
        print("A5.3 cross content_document:", cross.content_document)
        await step("A5.3 cross.query_selector_all", cross.query_selector_all("p"))
        await step("A5.3 cross.query_selector", cross.query_selector("p"))
        top = await tab.select("#top")
        await step("A5.8 tab.query_selector_all invalid", tab.query_selector_all("a[["))
        await step("A5.8 elem.query_selector_all invalid", top.query_selector_all("a[["))
        await step("A5.8 elem.query_selector invalid", top.query_selector("a[["))
        await step("A5.8 tab.query_selector invalid", tab.query_selector("a[["))
        outer = await tab.select("#outer")
        i2 = await outer.query_selector("#inner2")
        print("A8.8 inner2 node type:", type(i2.node).__name__, "tree:", type(i2.tree).__name__)
        print("A8.8 inner2.parent:", i2.parent)
        b = await outer.query_selector("#bold")
        print("A8.8 bold.parent:", b.parent, " parent.parent:", b.parent.parent if b.parent else "n/a")
        i2b = await tab.query_selector("#inner2")
        print("A8.8 control tab-level inner2.parent:", i2b.parent)
    finally:
        await browser.stop()
        srv.shutdown()


asyncio.run(main())
