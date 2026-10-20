import asyncio, sys, tempfile, pathlib, shutil
import zendriver as zd
from zendriver import cdp
print("zendriver from", zd.__file__, "python", sys.version.split()[0])

HTML = """<!doctype html><html><body>
<a id=lnk href="#x" onclick="window.c_lnk=(window.c_lnk||0)+1;return false">link</a>
<img id=img src="data:image/gif;base64,R0lGODlhAQABAAAAACw=" width=20 height=20 onclick="window.c_img=(window.c_img||0)+1">
<button id=b onclick="window.c_b=(window.c_b||0)+1">b</button>
</body></html>"""

async def attempt(tab, label, coro_fn, counter):
    try:
        r = await asyncio.wait_for(coro_fn(), 20)
        res = f"ok -> {r!r}"[:80]
    except Exception as e:
        res = f"EXC {type(e).__name__}: {str(e)[:80]}"
    c = await tab.evaluate(f"window.{counter}===undefined?null:window.{counter}")
    print(f"[{label}] {res}; counter={c}")

async def main():
    tmp = pathlib.Path(tempfile.mkdtemp(dir="/tmp/claude-0/-home-user-zendriver/b2021b39-94e6-5220-9e66-7f33c0314a80/scratchpad/verify/R13-refute/"))
    f = tmp / "page.html"; f.write_text(HTML)
    browser = await zd.start(headless=True)
    try:
        tab = await browser.get(f.as_uri())
        await tab.sleep(0.5)
        links = await tab.get_all_linked_sources()
        lnk = next(l for l in links if l.get("id") == "lnk")
        print("tree is None:", lnk.tree is None)
        await attempt(tab, "linked lnk.click #1", lambda: lnk.click(), "c_lnk")
        await attempt(tab, "linked lnk.click #2", lambda: lnk.click(), "c_lnk")
        lnk2 = next(l for l in await tab.get_all_linked_sources() if l.get("id") == "lnk")
        await attempt(tab, "fresh linked lnk.mouse_click #1", lambda: lnk2.mouse_click(), "c_lnk")
        await attempt(tab, "same lnk.mouse_click #2", lambda: lnk2.mouse_click(), "c_lnk")
        await attempt(tab, "same lnk.mouse_move", lambda: lnk2.mouse_move(), "c_lnk")
        await attempt(tab, "same lnk.get_position", lambda: lnk2.get_position(), "c_lnk")
        lnk3 = next(l for l in await tab.get_all_linked_sources() if l.get("id") == "lnk")
        await lnk3.update()
        print("after update tree is None:", lnk3.tree is None)
        await attempt(tab, "updated lnk.click", lambda: lnk3.click(), "c_lnk")
        img = next(l for l in await tab.get_all_linked_sources() if l.get("id") == "img")
        await attempt(tab, "linked img.click", lambda: img.click(), "c_img")
        # user-constructed element without tree
        b = await tab.select("#b")
        nb = zd.core.element.create(b.node, tab)
        await attempt(tab, "create(node, tab) b.click", lambda: nb.click(), "c_b")
        # other paths that produce elements: children/parent of selected element
        body = await tab.select("body")
        kids = body.children
        print("children tree None?", [k.tree is None for k in kids])
        # find / find_all / select_all / xpath trees
        for name, fn in [("find", lambda: tab.find("link")), ("select_all", lambda: tab.select_all("a")),
                         ("find_all", lambda: tab.find_all("link")), ("xpath", lambda: tab.xpath("//a"))]:
            try:
                r = await asyncio.wait_for(fn(), 20)
                r = r if isinstance(r, list) else [r]
                print(f"[{name}] tree None?", [x.tree is None for x in r])
            except Exception as e:
                print(f"[{name}] EXC {type(e).__name__}: {e}")
    finally:
        await browser.stop()
        shutil.rmtree(tmp, ignore_errors=True)

asyncio.run(asyncio.wait_for(main(), 100))
