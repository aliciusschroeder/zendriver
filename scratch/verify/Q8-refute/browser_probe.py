import asyncio, sys, traceback, urllib.parse
import zendriver
from zendriver import cdp
print("zendriver from", zendriver.__file__, "py", sys.version.split()[0])

HTML = """<html><head><link rel=stylesheet href="/x.css" items="3"></head><body>
<div id=wrap><my-list id=ml items='[1,2]'><a href="http://example.com/in">in</a></my-list></div>
<p>text before<br id=b clear=all>after</p>
<span id=s get=g>gspan</span>
<a id=lnk href="http://example.com/a">plain</a>
<svg id=sv><filter id=f><feColorMatrix id=fcm type=matrix values="1 0 0 0 0"/></filter></svg>
<div id=container><p id=p1>hello</p></div>
</body></html>"""

def attempt(label, fn):
    try:
        r = fn()
        print(f"[OK ] {label}: {str(r)[:120]!s}")
    except Exception as e:
        print(f"[ERR] {label}: {type(e).__name__}: {e}")

async def aattempt(label, coro_fn):
    try:
        r = await asyncio.wait_for(coro_fn(), 15)
        print(f"[OK ] {label}: {str(r)[:120]!s}")
    except Exception as e:
        print(f"[ERR] {label}: {type(e).__name__}: {e}")

async def main():
    browser = await zendriver.start(headless=True)
    try:
        tab = await browser.get("data:text/html," + urllib.parse.quote(HTML))
        await tab.sleep(0.5)
        # Chrome behaviour: raw attribute list
        doc = await tab.send(cdp.dom.get_document(-1, True))
        for sel in ("#b", "#ml", "#s", "#fcm"):
            nid = await tab.send(cdp.dom.query_selector(doc.node_id, sel))
            node = await tab.send(cdp.dom.describe_node(node_id=nid))
            print("CDP attributes for", sel, "->", node.attributes)
        br = await tab.select("#b")
        attempt("br.attrs", lambda: dict(br.attrs))
        await aattempt("await br (update)", lambda: br.update())
        await aattempt("br.query_selector('x')", lambda: br.query_selector("x"))
        await aattempt("br.click()", lambda: br.click())
        await aattempt("br.get_position()", lambda: br.get_position())
        attempt("repr(br)", lambda: repr(br))
        ml = await tab.select("#ml")
        attempt("repr(my-list items)", lambda: repr(ml))
        wrap = await tab.select("#wrap")
        attempt("str(wrap) (ancestor of items)", lambda: str(wrap))
        attempt("ml.get('id')", lambda: ml.get("id"))
        await aattempt("await ml (update)", lambda: ml.update())
        s = await tab.select("#s")
        attempt("s.get('id')", lambda: s.get("id"))
        attempt("s['id']", lambda: s["id"])
        attempt("s.id (deprecated __getattr__)", lambda: s.id)
        attempt("repr(s)", lambda: repr(s))
        await aattempt("await s (update)", lambda: s.update())
        fcm = await tab.select("#fcm")
        attempt("fcm.attrs.values()", lambda: list(fcm.attrs.values()))
        attempt("repr(fcm)", lambda: repr(fcm))
        await aattempt("tab.get_all_urls()", lambda: tab.get_all_urls())
        await aattempt("tab.get_all_urls(absolute=False)", lambda: tab.get_all_urls(absolute=False))
        await aattempt("br.get_js_attributes().clear()", lambda: _js_clear(br))
        # control
        c = await tab.select("#container")
        await aattempt("control: await container", lambda: c.update())
        attempt("control: repr(container)", lambda: repr(c))
        # find by text paths (br is a void element; find text inside p)
        await aattempt("tab.find('text before')", lambda: tab.find("text before", best_match=True))
        await aattempt("tab.select_all('br')", lambda: tab.select_all("br"))
    finally:
        await browser.stop()

async def _js_clear(el):
    js = await el.get_js_attributes()
    print("   js keys has clear:", "clear" in js, "values" in js, "items" in js, "get" in js)
    return js.clear()

asyncio.run(main())
