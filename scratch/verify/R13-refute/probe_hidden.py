import asyncio, sys, traceback, tempfile, pathlib, shutil
import zendriver as zd
from zendriver import cdp
print("zendriver from", zd.__file__, "python", sys.version.split()[0])

HTML = """<!doctype html><html><head><style>.vh{position:absolute;width:1px;height:1px;overflow:hidden;clip:rect(0 0 0 0)}</style></head><body>
<button id=vis onclick="window.c_vis=(window.c_vis||0)+1">visible</button>
<button id=dn style="display:none" onclick="window.c_dn=(window.c_dn||0)+1">dn</button>
<div style="display:none"><button id=parentdn onclick="window.c_parentdn=(window.c_parentdn||0)+1">p</button></div>
<button id=vhid style="visibility:hidden" onclick="window.c_vhid=(window.c_vhid||0)+1">vh</button>
<button id=op0 style="opacity:0" onclick="window.c_op0=(window.c_op0||0)+1">op0</button>
<input id=cb type=checkbox class=vh onclick="window.c_cb=(window.c_cb||0)+1">
<button id=zero style="width:0;height:0;padding:0;border:0;overflow:hidden" onclick="window.c_zero=(window.c_zero||0)+1"></button>
<input id=file type=file style="display:none" onclick="window.c_file=(window.c_file||0)+1">
<input id=hiddeninp type=hidden onclick="window.c_hiddeninp=(window.c_hiddeninp||0)+1">
<details><summary>s</summary><button id=indetails onclick="window.c_indetails=(window.c_indetails||0)+1">d</button></details>
<button hidden id=hattr onclick="window.c_hattr=(window.c_hattr||0)+1">h</button>
<a id=lnk href="#x" onclick="window.c_lnk=(window.c_lnk||0)+1;return false">link</a>
<img id=img src="data:image/gif;base64,R0lGODlhAQABAAAAACw=" onclick="window.c_img=(window.c_img||0)+1">
</body></html>"""

async def main():
    tmp = pathlib.Path(tempfile.mkdtemp(dir="/tmp/claude-0/-home-user-zendriver/b2021b39-94e6-5220-9e66-7f33c0314a80/scratchpad/verify/R13-refute/"))
    f = tmp / "page.html"; f.write_text(HTML)
    browser = await zd.start(headless=True)
    try:
        tab = await browser.get(f.as_uri())
        await tab.sleep(0.5)
        print("chrome version:", (await browser.connection.send(cdp.browser.get_version()))[1])
        # raw Chrome behaviour of DOM.getContentQuads
        for sel in ["vis","dn","parentdn","vhid","op0","cb","zero","file","hiddeninp","indetails","hattr"]:
            el = await tab.select("#"+sel)
            ro = await tab.send(cdp.dom.resolve_node(backend_node_id=el.backend_node_id))
            try:
                q = await tab.send(cdp.dom.get_content_quads(object_id=ro.object_id))
                print(f"[raw quads] {sel}: {q!r}")
            except Exception as e:
                print(f"[raw quads] {sel}: EXC {type(e).__name__}: {e}")
        # detached
        await tab.evaluate("window._det=document.createElement('button'); window._det.onclick=()=>{window.c_det=1}; 0")
        ro, _ = await tab.send(cdp.runtime.evaluate("window._det"))
        try:
            q = await tab.send(cdp.dom.get_content_quads(object_id=ro.object_id))
            print(f"[raw quads] detached: {q!r}")
        except Exception as e:
            print(f"[raw quads] detached: EXC {type(e).__name__}: {e}")

        for sel in ["vis","dn","parentdn","vhid","op0","cb","zero","file","hiddeninp","indetails","hattr"]:
            el = await tab.select("#"+sel)
            print(f"  tree set: {el.tree is not None}")
            try:
                await asyncio.wait_for(el.click(), 20)
                res = "ok"
            except Exception as e:
                res = f"EXC {type(e).__name__}: {str(e)[:90]}"
            cnt = await tab.evaluate(f"window.c_{sel}===undefined?null:window.c_{sel}")
            print(f"[click] {sel}: {res}; js-click-counter={cnt}")
        # JS-only click baseline on hidden
        el = await tab.select("#dn")
        await el.apply("(e)=>e.click()")
        print("[apply click] dn counter:", await tab.evaluate("window.c_dn"))
        # mouse_* and screenshot on dn
        for name, coro in [("mouse_click", lambda e: e.mouse_click()), ("mouse_move", lambda e: e.mouse_move()),
                           ("mouse_drag", lambda e: e.mouse_drag((10,10))), ("screenshot_b64", lambda e: e.screenshot_b64()),
                           ("flash", lambda e: e.flash()), ("get_position", lambda e: e.get_position())]:
            el = await tab.select("#dn")
            try:
                r = await asyncio.wait_for(coro(el), 20)
                print(f"[{name}] dn: returned {r!r}"[:150])
            except Exception as e:
                print(f"[{name}] dn: EXC {type(e).__name__}: {str(e)[:90]}")
    finally:
        await browser.stop()
        shutil.rmtree(tmp, ignore_errors=True)

asyncio.run(asyncio.wait_for(main(), 100))
