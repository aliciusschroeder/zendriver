import asyncio
import sys

sys.path.insert(0, "/tmp/claude-0/-home-user-zendriver/b2021b39-94e6-5220-9e66-7f33c0314a80/scratchpad/verify/BC-refute")
import zendriver as zd
from zendriver import cdp
from helper import PAGES, serve, show, desc

print("zendriver from", zd.__file__, "python", sys.version.split()[0])


def find_nodes(n, pred, out=None):
    if out is None:
        out = []
    if pred(n):
        out.append(n)
    for c in n.children or []:
        find_nodes(c, pred, out)
    for s in n.shadow_roots or []:
        find_nodes(s, pred, out)
    if n.content_document:
        find_nodes(n.content_document, pred, out)
    return out


async def main():
    srv, port = serve()
    PAGES["/main"] = f"""<html><body>
<div id="outer"><div id="inner">inner text</div><p id="deep">deep <b id="bold">bold</b></p></div>
<input id="topinput" placeholder="Top placeholder">
<iframe id="cross" src="http://localhost:{port}/cross"></iframe>
</body></html>"""
    PAGES["/cross"] = "<html><body><p>cross p</p></body></html>"
    PAGES["/ph"] = """<html><body><p>x</p><iframe id="fr" srcdoc="<input placeholder='Search needle'>"></iframe></body></html>"""
    PAGES["/sh"] = """<html><body><p>y</p><iframe id="fr" src="/shinner"></iframe></body></html>"""
    PAGES["/shinner"] = """<html><body><div id="host"></div><script>
document.getElementById('host').attachShadow({mode:'open'}).innerHTML='<b>shadow needle</b>';</script></body></html>"""
    browser = await zd.start(headless=True)
    try:
        base = f"http://127.0.0.1:{port}"
        tab = await browser.get(base + "/main")
        await tab.sleep(1.5)

        print("=== control: main-doc placeholder find")
        r = await show("find_elements_by_text('Top placeholder')", tab.find_elements_by_text("Top placeholder"))
        print("   ", desc(r) if isinstance(r, list) else r)

        print("\n=== A5.3 cross-origin iframe")
        cross = await tab.select("#cross")
        print("cross content_document:", cross.content_document)
        await show("cross.query_selector_all('p')", cross.query_selector_all("p"))
        await show("cross.query_selector('p')", cross.query_selector("p"))

        print("\n=== A5.8/B15.7 invalid selector")
        outer = await tab.select("#outer")
        await show("tab.query_selector_all('a[[')", tab.query_selector_all("a[["))
        await show("tab.query_selector('a[[')", tab.query_selector("a[["))
        await show("outer.query_selector_all('a[[')", outer.query_selector_all("a[["))
        await show("outer.query_selector('a[[')", outer.query_selector("a[["))
        await show("tab.select('a[[', timeout=1)", tab.select("a[[", timeout=1))
        print("outer __last leftover:", getattr(outer, "__last", None))

        print("\n=== A8.8 element-scoped query result .parent")
        inner = await outer.query_selector("#inner")
        print("inner node type:", type(inner.node).__name__, "tree type:", type(inner.tree).__name__)
        print("inner.parent:", desc(inner.parent))
        inner_tab = await tab.query_selector("#inner")
        print("tab-level inner.parent:", desc(inner_tab.parent))
        bold = await outer.query_selector("#bold")
        bp = bold.parent
        print("bold.parent:", desc(bp), "bold.parent.parent:", desc(bp.parent) if bp else None)
        qsa = await outer.query_selector_all("div")
        print("qsa div parents:", [desc(x.parent) for x in qsa])
        await inner.update()
        print("after inner.update(): parent", desc(inner.parent), type(inner.node).__name__)

        print("\n=== A6.2 iframe UA shadow placeholder")
        tab = await browser.get(base + "/ph")
        await tab.sleep(1.0)
        doc = await tab.send(cdp.dom.get_document(-1, True))
        inputs = find_nodes(doc, lambda n: n.node_name == "INPUT")
        for i in inputs:
            print("   INPUT shadow_roots:", [(s.shadow_root_type, len(s.children or [])) for s in (i.shadow_roots or [])])
        sid, n = await tab.send(cdp.dom.perform_search("needle", True))
        print("   performSearch needle n=", n)
        await show("find_elements_by_text('needle')", tab.find_elements_by_text("needle"))
        await show("find('needle', timeout=2)", tab.find("needle", timeout=2))
        await show("find_all('needle', timeout=2)", tab.find_all("needle", timeout=2))
        await show("wait_for(text='needle', timeout=2)", tab.wait_for(text="needle", timeout=2))
        try:
            await tab.find_elements_by_text("needle")
        except AttributeError:
            import traceback; traceback.print_exc(limit=-2)

        print("\n=== A6.2 iframe open shadow root")
        tab = await browser.get(base + "/sh")
        await tab.sleep(1.0)
        await show("find('shadow needle', timeout=2)", tab.find("shadow needle", timeout=2))
        await show("find_all('shadow needle', timeout=2)", tab.find_all("shadow needle", timeout=2))
        print("   control: find('y'):", desc(await tab.find("y", timeout=2)) if False else "skip")
        await show("find('zzz-nomatch', timeout=1)", tab.find("zzz-nomatch", timeout=1))
    finally:
        await browser.stop()
        srv.shutdown()


asyncio.run(asyncio.wait_for(main(), 100))
