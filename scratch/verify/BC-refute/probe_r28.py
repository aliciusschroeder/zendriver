import asyncio
import sys

sys.path.insert(0, "/tmp/claude-0/-home-user-zendriver/b2021b39-94e6-5220-9e66-7f33c0314a80/scratchpad/verify/BC-refute")
import zendriver as zd
from zendriver import cdp
from helper import PAGES, serve, show, desc

print("zendriver from", zd.__file__, "python", sys.version.split()[0])

PAGES["/main"] = """<html><body>
<div id="top"><p id="topp">top paragraph</p></div>
<iframe id="fr" srcdoc="<div id='box' data-v='1'><p id='inner'>inner para</p><span>a</span><b>bold inner</b></div>"></iframe>
<iframe id="fr2" src="/same"></iframe>
</body></html>"""
PAGES["/same"] = """<html><body><div id="inner2"><span class="s">hello same origin</span><b>bold2</b>
<button onclick="window.clicked=1">inner needle</button></div></body></html>"""


def walk(n, depth=0, out=None):
    if out is None:
        out = []
    out.append((depth, n.node_name, n.node_id, bool(n.content_document), len(n.children or [])))
    for c in n.children or []:
        walk(c, depth + 1, out)
    if n.content_document:
        walk(n.content_document, depth + 1, out)
    return out


async def main():
    srv, port = serve()
    browser = await zd.start(headless=True)
    try:
        base = f"http://127.0.0.1:{port}"
        tab = await browser.get(base + "/main")
        await tab.sleep(1.5)
        js_inner = "document.getElementById('fr').contentDocument.getElementById('inner') !== null"
        print("JS: inner exists:", await tab.evaluate(js_inner))

        # Chrome behaviour: getDocument pierce includes content_document; IFRAME .children
        doc = await tab.send(cdp.dom.get_document(-1, True))
        for row in walk(doc):
            if row[1] in ("IFRAME", "#document", "P", "B", "SPAN", "BUTTON", "DIV"):
                print("  tree", row)
        # performSearch hits inside iframes?
        sid, n = await tab.send(cdp.dom.perform_search("hello same origin", True))
        ids = await tab.send(cdp.dom.get_search_results(sid, 0, n)) if n else []
        print("performSearch 'hello same origin' n=", n, ids)
        for i in ids:
            d = await tab.send(cdp.dom.describe_node(node_id=i))
            print("   described:", d.node_name, d.node_type, d.parent_id)

        print("\n=== A9.4 iframe.query_selector -> remove_from_dom")
        iframe = await tab.select("#fr")
        inner = await iframe.query_selector("#inner")
        print("inner:", desc(inner), "parent:", desc(inner.parent))
        await show("inner.remove_from_dom", inner.remove_from_dom())
        print("parent after remove_from_dom:", desc(inner.parent))
        print("JS: inner still exists in iframe:", await tab.evaluate(js_inner))
        topp = await tab.select("#topp")
        await topp.remove_from_dom()
        print("control JS: topp still exists:", await tab.evaluate("document.getElementById('topp') !== null"))

        print("\n=== A8.9 update() on iframe element")
        iframe = await tab.select("#fr")
        box = await iframe.query_selector("#box")
        print("box data-v", box.get("data-v"), "parent", desc(box.parent))
        await tab.evaluate("document.getElementById('fr').contentDocument.getElementById('box').setAttribute('data-v','2')")
        await box.update()
        print("after update: data-v", box.get("data-v"), "parent", desc(box.parent))

        print("\n=== A5.4 select(include_frames) then element-scoped query")
        inner2 = await tab.select("#inner2", include_frames=True)
        print("inner2:", desc(inner2), "children:", desc(inner2.children))
        nid_before = inner2.node_id
        await show("inner2.query_selector_all('b')", inner2.query_selector_all("b"))
        await show("inner2.query_selector('b')", inner2.query_selector("b"))
        print("node_id before/after:", nid_before, inner2.node_id)

        print("\n=== A5.5a select_all('span', include_frames) parent")
        spans = await tab.select_all("span", include_frames=True)
        for s in spans:
            print(" span", desc(s), "parent", desc(s.parent))

        print("\n=== A5.9/A6.3 text search inside same-origin iframe")
        r = await show("find_all('hello same origin')", tab.find_all("hello same origin", timeout=3))
        if isinstance(r, list):
            print("   desc", desc(r))
        r = await show("find(best_match=False)", tab.find("hello same origin", best_match=False, timeout=3))
        print("   desc", desc(r) if not isinstance(r, Exception) else r)
        r = await show("find(best_match=True)", tab.find("hello same origin", best_match=True, timeout=3))
        print("   desc", desc(r) if not isinstance(r, Exception) else r)
        el = await show("wait_for(text='inner needle')", tab.wait_for(text="inner needle", timeout=3))
        if not isinstance(el, Exception):
            print("   desc", desc(el))
            await show("click text node", el.click())
            print("   clicked:", await tab.evaluate("document.getElementById('fr2').contentWindow.clicked"))
        el2 = await tab.find("inner needle", best_match=True, timeout=3)
        print("   best_match elem", desc(el2))
        await el2.click()
        print("   clicked after best_match:", await tab.evaluate("document.getElementById('fr2').contentWindow.clicked"))
    finally:
        await browser.stop()
        srv.shutdown()


asyncio.run(asyncio.wait_for(main(), 100))
