import asyncio
import sys
import tempfile
import pathlib
import traceback

import zendriver
from zendriver import cdp

print("zendriver from:", zendriver.__file__, "python", sys.version.split()[0])

HTML = """<!doctype html><html><body>
<button id="vis" onclick="window.visClicked=(window.visClicked||0)+1">visible</button>
<button id="hid" style="display:none" onclick="window.hidClicked=(window.hidClicked||0)+1">hidden</button>
<span style="visibility:hidden"><button id="vh" onclick="window.vhClicked=(window.vhClicked||0)+1">vh</button></span>
<a id="lnk" href="#x" onclick="window.lnkClicks=(window.lnkClicks||0)+1; return false;">link</a>
<input id="file" type="file" style="display:none" onclick="window.fileClicked=1">
</body></html>"""


async def attempt(label, coro):
    try:
        r = await asyncio.wait_for(coro, 15)
        print(f"[{label}] OK -> {r!r}")
    except Exception as e:
        print(f"[{label}] EXC {type(e).__name__}: {str(e)[:150]}")


async def main():
    tmp = tempfile.mkdtemp(prefix="r13fs_", dir=str(pathlib.Path(__file__).parent))
    page = pathlib.Path(tmp) / "p.html"
    page.write_text(HTML)
    browser = await zendriver.start(headless=True)
    try:
        tab = await browser.get(page.as_uri())
        await tab.sleep(0.5)

        hid = await tab.query_selector("#hid")
        # raw CDP: what does getContentQuads return for display:none?
        ro = await tab.send(cdp.dom.resolve_node(backend_node_id=hid.backend_node_id))
        try:
            q = await tab.send(cdp.dom.get_content_quads(object_id=ro.object_id))
            print("[raw quads display:none]", q)
        except Exception as e:
            print("[raw quads display:none] EXC", type(e).__name__, e)

        await attempt("get_position hidden", hid.get_position())
        await attempt("click hidden", hid.click())
        print("   window.hidClicked =", await tab.evaluate("window.hidClicked"))
        await attempt("mouse_click hidden", hid.mouse_click())
        await attempt("mouse_move hidden", hid.mouse_move())
        await attempt("flash hidden", hid.flash())
        await attempt("screenshot_b64 hidden", hid.screenshot_b64())

        vh = await tab.query_selector("#vh")
        await attempt("get_position visibility:hidden", vh.get_position())

        vis = await tab.query_selector("#vis")
        await attempt("click visible", vis.click())
        print("   window.visClicked =", await tab.evaluate("window.visClicked"))

        f = await tab.query_selector("#file")
        await attempt("click hidden file input", f.click())
        print("   window.fileClicked =", await tab.evaluate("window.fileClicked"))

        links = await tab.get_all_linked_sources()
        lnk = next(l for l in links if l.get("id") == "lnk")
        print("[lnk tree]", lnk.tree)
        await attempt("lnk click 1", lnk.click())
        await attempt("lnk click 2", lnk.click())
        print("   window.lnkClicks =", await tab.evaluate("window.lnkClicks"))
        links = await tab.get_all_linked_sources()
        lnk2 = next(l for l in links if l.get("id") == "lnk")
        await attempt("lnk2 mouse_click 1", lnk2.mouse_click())
        await attempt("lnk2 mouse_click 2", lnk2.mouse_click())
        await attempt("lnk2 get_position", lnk2.get_position())

        # detached node: what does getContentQuads do?
        det_ro = await tab.send(cdp.runtime.evaluate("(()=>{const b=document.createElement('button'); b.onclick=()=>{window.detClicked=1}; return b})()"))
        det_ro = det_ro[0]
        try:
            q = await tab.send(cdp.dom.get_content_quads(object_id=det_ro.object_id))
            print("[raw quads detached]", q)
        except Exception as e:
            print("[raw quads detached] EXC", type(e).__name__, e)
        # removed-from-dom element
        vis2 = await tab.query_selector("#vis")
        await tab.evaluate("document.getElementById('vis').remove()")
        await attempt("get_position removed (cached ro)", vis2.get_position())
        await attempt("click removed", vis2.click())
        print("   window.visClicked =", await tab.evaluate("window.visClicked"))
    finally:
        await browser.stop()
        import shutil
        shutil.rmtree(tmp, ignore_errors=True)


asyncio.run(main())
