import asyncio, sys, pathlib
sys.path.insert(0, sys.argv[1] + "/tests")
from pngutil import png_center
import zendriver
print("zendriver from", zendriver.__file__)
PAGE = """<!doctype html><html><head><style>body{margin:0}</style></head><body>
<div style="width:300px;height:3000px;background:rgb(255,0,0)"></div>
<div id=fix style="position:fixed;top:50px;left:20px;width:100px;height:60px;background:rgb(0,0,255)"></div>
<div id=sticky style="position:sticky;bottom:0;width:100px;height:60px;background:rgb(0,255,0)"></div>
<div style="height:1000px;background:rgb(255,0,0)"></div>
</body></html>"""
async def main():
    p = pathlib.Path(sys.argv[1]) / "page_fixed.html"; p.write_text(PAGE)
    browser = await zendriver.start(headless=True)
    try:
        tab = await browser.get(p.as_uri()); await tab.sleep(0.3)
        for scroll in (0, 1100):
            await tab.evaluate(f"window.scrollTo(0,{scroll})"); await tab.sleep(0.2)
            for sel in ("#fix", "#sticky"):
                el = await tab.select(sel)
                pos = await el.get_position()
                try:
                    r = png_center(await asyncio.wait_for(el.screenshot_b64(format="png"), 15))
                except Exception as e:
                    r = f"EXC {type(e).__name__}: {str(e).splitlines()[0]}"
                print(f"scroll={scroll} {sel} pos={pos} -> {r}")
    finally:
        await browser.stop()
asyncio.run(main())
