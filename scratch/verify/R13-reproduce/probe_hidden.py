import asyncio
import logging
import pathlib
import sys
import tempfile
import traceback

import zendriver
from zendriver.core.connection import ProtocolException

print("zendriver from", zendriver.__file__, "python", sys.version.split()[0])

HTML = """<!doctype html><html><head><title>r13</title></head><body>
<button id="vis" onclick="window.visClicked=(window.visClicked||0)+1">visible</button>
<button id="hid" style="display:none" onclick="window.hidClicked=(window.hidClicked||0)+1">hidden</button>
<div style="display:none"><button id="nested" onclick="window.nestedClicked=(window.nestedClicked||0)+1">nested</button></div>
<input type="file" id="file" style="display:none" onclick="window.fileClicked=(window.fileClicked||0)+1">
<a id="lnk" href="#x" onclick="window.lnkClicks=(window.lnkClicks||0)+1; return false;">link</a>
</body></html>"""


async def attempt(label, coro_fn):
    try:
        r = await asyncio.wait_for(coro_fn(), 20)
        print(f"[{label}] OK -> {r!r}"[:300])
        return None
    except Exception as e:  # noqa
        print(f"[{label}] EXC {type(e).__module__}.{type(e).__name__}: {str(e)[:160]}")
        return e


async def main():
    tmp = pathlib.Path(tempfile.mkdtemp(prefix="r13repro-"))
    page = tmp / "page.html"
    page.write_text(HTML)
    browser = await zendriver.start(headless=True)
    try:
        tab = await browser.get(page.as_uri())
        await tab.wait_for_ready_state("complete")

        # --- Control: visible button click works
        vis = await tab.select("#vis")
        await attempt("vis click", vis.click)
        print("  window.visClicked =", await tab.evaluate("window.visClicked"))

        # --- A8.3 / B15.6: click() on display:none
        hid = await tab.select("#hid")
        print("  hid tree is None?", hid.tree is None)
        # raw CDP: what do content quads return for display:none?
        ro = await tab.send(zendriver.cdp.dom.resolve_node(backend_node_id=hid.backend_node_id))
        try:
            q = await tab.send(zendriver.cdp.dom.get_content_quads(object_id=ro.object_id))
            print("  raw DOM.getContentQuads for #hid ->", q)
        except ProtocolException as e:
            print("  raw DOM.getContentQuads for #hid -> ProtocolException", e)

        e = await attempt("hid click", hid.click)
        if e is not None:
            traceback.print_exception(e, limit=-3)
        print("  window.hidClicked after click() =", await tab.evaluate("window.hidClicked"))
        # proof that a JS el.click() works on the hidden element
        await attempt("hid apply el.click()", lambda: hid.apply("(el) => el.click()"))
        print("  window.hidClicked after apply(el.click) =", await tab.evaluate("window.hidClicked"))

        # nested hidden + hidden file input
        nested = await tab.select("#nested")
        await attempt("nested click", nested.click)
        print("  window.nestedClicked =", await tab.evaluate("window.nestedClicked"))
        fin = await tab.select("#file")
        await attempt("file-input click", fin.click)
        print("  window.fileClicked =", await tab.evaluate("window.fileClicked"))

        # get_position contract
        await attempt("hid get_position (annotated Position|None)", hid.get_position)
        # mouse_* graceful branches
        await attempt("hid mouse_click (should warn+return)", hid.mouse_click)
        await attempt("hid mouse_move (should warn+return)", hid.mouse_move)
        await attempt("hid mouse_drag -> (10,10) (should warn+return)", lambda: hid.mouse_drag((10, 10)))
        await attempt("vis mouse_drag -> hid element (should warn+return)", lambda: vis.mouse_drag(hid))
        await attempt("hid flash (should warn+return)", hid.flash)
        e = await attempt("hid screenshot_b64 (doc: RuntimeError)", hid.screenshot_b64)
        print("  screenshot_b64 exception is RuntimeError?", isinstance(e, RuntimeError))

        # --- A8.4: tree-less Element from get_all_linked_sources
        links = await tab.get_all_linked_sources()
        lnk = next(l for l in links if l.get("id") == "lnk")
        print("  lnk tree:", lnk.tree, " _remote_object:", lnk._remote_object)
        e = await attempt("lnk click 1", lnk.click)
        if e is not None:
            traceback.print_exception(e, limit=-3)
        print("  window.lnkClicks after click 1 =", await tab.evaluate("window.lnkClicks"))
        await attempt("lnk click 2", lnk.click)
        print("  window.lnkClicks after click 2 =", await tab.evaluate("window.lnkClicks"))
        await attempt("lnk get_position", lnk.get_position)
        await attempt("lnk mouse_move", lnk.mouse_move)
        await attempt("lnk flash", lnk.flash)
        await attempt("lnk screenshot_b64", lnk.screenshot_b64)

        # fresh tree-less element: first mouse_click short-circuits, second fails
        links2 = await tab.get_all_linked_sources()
        lnk2 = next(l for l in links2 if l.get("id") == "lnk")
        await attempt("lnk2 mouse_click 1 (fresh)", lnk2.mouse_click)
        await asyncio.sleep(0.3)
        print("  window.lnkClicks after lnk2 mouse_click 1 =", await tab.evaluate("window.lnkClicks"))
        await attempt("lnk2 mouse_click 2", lnk2.mouse_click)
        await asyncio.sleep(0.3)
        print("  window.lnkClicks after lnk2 mouse_click 2 =", await tab.evaluate("window.lnkClicks"))

        # tree-less element after update() works (documented workaround)
        links3 = await tab.get_all_linked_sources()
        lnk3 = next(l for l in links3 if l.get("id") == "lnk")
        await lnk3.update()
        print("  lnk3 tree after update() is None?", lnk3.tree is None)
        await attempt("lnk3 click after update()", lnk3.click)
        print("  window.lnkClicks after lnk3 click =", await tab.evaluate("window.lnkClicks"))

        # other tree-less producers? query_selector results
        q = await tab.query_selector("#lnk")
        print("  query_selector #lnk tree is None?", q.tree is None)
    finally:
        await browser.stop()
        import shutil

        shutil.rmtree(tmp, ignore_errors=True)


asyncio.run(main())
