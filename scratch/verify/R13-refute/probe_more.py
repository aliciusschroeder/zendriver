import asyncio, sys, tempfile, pathlib, shutil
import zendriver as zd
from zendriver import cdp
print("zendriver from", zd.__file__, "python", sys.version.split()[0])
HTML = """<!doctype html><html><body>
<select id=sel onchange="window.c_change=(window.c_change||0)+1"><option value=a>a</option><option id=opt value=b onclick="window.c_opt=(window.c_opt||0)+1">b</option></select>
<div id=dc style="display:contents" onclick="window.c_dc=(window.c_dc||0)+1"><span>inside contents</span></div>
<ul><li id=menuitem style="display:none" onclick="window.c_menuitem=(window.c_menuitem||0)+1">hidden menu item</li></ul>
</body></html>"""
async def main():
    tmp = pathlib.Path(tempfile.mkdtemp(dir="/tmp/claude-0/-home-user-zendriver/b2021b39-94e6-5220-9e66-7f33c0314a80/scratchpad/verify/R13-refute/"))
    f = tmp / "page.html"; f.write_text(HTML)
    browser = await zd.start(headless=True)
    try:
        tab = await browser.get(f.as_uri()); await tab.sleep(0.5)
        for sel in ["opt", "dc", "menuitem"]:
            el = await tab.select("#"+sel)
            ro = await tab.send(cdp.dom.resolve_node(backend_node_id=el.backend_node_id))
            try:
                q = await tab.send(cdp.dom.get_content_quads(object_id=ro.object_id)); print(f"[raw quads] {sel}: {q!r}")
            except Exception as e:
                print(f"[raw quads] {sel}: EXC {type(e).__name__}: {e}")
            try:
                await asyncio.wait_for(el.click(), 20); res="ok"
            except Exception as e:
                res=f"EXC {type(e).__name__}: {str(e)[:70]}"
            print(f"[click] {sel}: {res}; counter={await tab.evaluate(f'window.c_{sel}===undefined?null:window.c_{sel}')}")
        # find by text on hidden element
        el = await tab.find("hidden menu item")
        print("find() returned hidden element:", el)
        opt = await tab.select("#opt")
        try:
            await opt.select_option(); print("select_option ok, value:", await tab.evaluate("document.getElementById('sel').value"))
        except Exception as e:
            print("select_option EXC", type(e).__name__, e)
    finally:
        await browser.stop(); shutil.rmtree(tmp, ignore_errors=True)
asyncio.run(asyncio.wait_for(main(), 100))
