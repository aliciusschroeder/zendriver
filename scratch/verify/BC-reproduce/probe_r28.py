import asyncio
import sys

sys.path.insert(0, __file__.rsplit("/", 1)[0])
from common import PAGES, serve, desc, step, browser_ctx, wait_loaded  # noqa

PAGES["/main"] = (
    "<html><body>"
    "<div id='top'><p id='topp'>top paragraph</p></div>"
    "<iframe id='fr' src='/same'></iframe>"
    "<iframe id='sd' srcdoc=\"<div id=box><p id=inner>srcdoc inner</p></div><div id=x data-v=1>xx</div>\"></iframe>"
    "</body></html>"
)
PAGES["/same"] = (
    "<html><body>"
    "<div id='inner2'><span class='s'>hello same origin</span><b>bold inner</b></div>"
    "<button id='btn' onclick='window.clicked=1'>inner needle</button>"
    "</body></html>"
)

FR = "document.getElementById('fr').contentDocument"
SD = "document.getElementById('sd').contentDocument"


async def main():
    srv = serve()
    port = srv.server_address[1]
    url = f"http://127.0.0.1:{port}/main"
    async with browser_ctx() as browser:
        tab = await browser.get(url)
        ok = await wait_loaded(
            tab,
            f"!!({FR} && {FR}.getElementById('btn') && {SD} && {SD}.getElementById('inner'))",
            True,
        )
        print("loaded:", ok)

        # control: top-level element
        topp = await tab.select("#topp")
        print("control topp.parent:", desc(topp.parent))
        topp2 = await tab.select("#topp")
        await topp2.remove_from_dom()
        print("control topp removed:", await tab.evaluate("document.getElementById('topp') === null"))

        print("\n=== A9.4 iframe.query_selector + remove_from_dom")
        iframe = await tab.select("#sd")
        inner = await iframe.query_selector("#inner")
        print("inner:", desc(inner), "inner.parent:", desc(inner.parent))
        await step("inner.remove_from_dom()", inner.remove_from_dom())
        print("inner.parent after remove_from_dom:", desc(inner.parent))
        print("srcdoc #inner still present:", await tab.evaluate(f"{SD}.getElementById('inner') !== null"))

        print("\n=== A9.4/A5.5(a) select_all include_frames -> parent")
        spans = await tab.select_all("span", include_frames=True)
        print("spans:", [desc(s) for s in spans])
        for s in spans:
            print("  span.parent:", desc(s.parent), "tree type:", type(s.tree).__name__, "tree name:", getattr(s.tree, 'node_name', None))

        print("\n=== A5.4 element inside iframe: query_selector(_all)")
        inner2 = await tab.select("#inner2", include_frames=True)
        print("inner2:", desc(inner2), "node_id", inner2.node_id)
        print("inner2.children:", [desc(c) for c in inner2.children])
        nid_before = inner2.node_id
        r = await step("inner2.query_selector_all('b')", inner2.query_selector_all("b"))
        r = await step("inner2.query_selector('b')", inner2.query_selector("b"))
        print("node_id before/after update:", nid_before, inner2.node_id)
        print("__last leftover:", getattr(inner2, "__last", None))

        print("\n=== A8.9 update() of element inside iframe -> stale attrs, parent lost")
        iframe = await tab.select("#sd")
        x = await iframe.query_selector("#x")
        print("x:", desc(x), "data-v:", x.get("data-v") if hasattr(x, 'get') else x.attrs.get('data-v'), "parent:", desc(x.parent))
        await tab.evaluate(f"{SD}.getElementById('x').setAttribute('data-v','2')")
        await step("x.update()", x.update())
        print("after update data-v:", x.attrs.get("data-v"), "parent:", desc(x.parent))
        await step("x.remove_from_dom()", x.remove_from_dom())
        print("srcdoc #x still present:", await tab.evaluate(f"{SD}.getElementById('x') !== null"))
        # control same on top-level element
        top = await tab.select("#top")
        await tab.evaluate("document.getElementById('top').setAttribute('data-v','9')")
        await top.update()
        print("control top data-v after update:", top.attrs.get("data-v"))

        print("\n=== A5.5(b) container.query_selector('p').parent")
        await tab.evaluate("document.body.insertAdjacentHTML('afterbegin', \"<div id='outer'><p id='deep'><b id='bold'>B</b></p><i id='direct'>i</i></div>\")")
        outer = await tab.select("#outer")
        p = await outer.query_selector("p")
        print("p:", desc(p), "type(p.node):", type(p.node).__name__, "type(p.tree):", type(p.tree).__name__)
        print("p.parent:", desc(p.parent))
        ps = await outer.query_selector_all("p")
        print("qsa p.parent:", [desc(q.parent) for q in ps])
        b = await outer.query_selector("#bold")
        bp = b.parent
        print("bold.parent:", desc(bp), "bold.parent.parent:", desc(bp.parent) if bp else 'n/a')
        tp = await tab.select("#deep")
        print("tab-level #deep.parent:", desc(tp.parent))

        print("\n=== A5.9 find_all/find on same-origin iframe text")
        r = await step("find_all('hello same origin')", tab.find_all("hello same origin", timeout=3))
        if isinstance(r, list):
            print("  ->", [desc(e) for e in r])
        r = await step("find('hello same origin', best_match=False)", tab.find("hello same origin", best_match=False, timeout=3))
        print("  ->", desc(r) if not isinstance(r, Exception) else r)
        r = await step("find('hello same origin', best_match=True)", tab.find("hello same origin", best_match=True, timeout=3))
        print("  ->", desc(r) if not isinstance(r, Exception) else r)

        print("\n=== A6.3 find_elements_by_text / wait_for(text) / click")
        r = await step("find_elements_by_text('inner needle')", tab.find_elements_by_text("inner needle"))
        if isinstance(r, list):
            print("  ->", [desc(e) for e in r])
        r = await step("find_element_by_text('inner needle')", tab.find_element_by_text("inner needle"))
        print("  ->", desc(r) if not isinstance(r, Exception) else r)
        el = await step("wait_for(text='inner needle')", tab.wait_for(text="inner needle", timeout=3))
        print("  ->", desc(el) if not isinstance(el, Exception) else el)
        if not isinstance(el, Exception):
            await step("el.click()", el.click())
            await asyncio.sleep(0.3)
            print("iframe window.clicked after text-node click:", await tab.evaluate("String(document.getElementById('fr').contentWindow.clicked)"))
        el2 = await tab.find("inner needle", best_match=True, timeout=3)
        print("best_match el:", desc(el2))
        await el2.click()
        await asyncio.sleep(0.3)
        print("iframe window.clicked after best_match click:", await tab.evaluate("String(document.getElementById('fr').contentWindow.clicked)"))
    srv.shutdown()


asyncio.run(asyncio.wait_for(main(), 100))
