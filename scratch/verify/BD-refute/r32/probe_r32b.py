import asyncio, sys, pathlib, time
import zendriver as zd
from zendriver import cdp
print("zendriver from", zd.__file__, sys.version.split()[0])
HERE = pathlib.Path(__file__).parent

async def pixel(tab, b64, fmt="png"):
    js = f"""new Promise(res => {{ const im = new Image(); im.onload = () => {{
        const c = document.createElement('canvas'); c.width = im.width; c.height = im.height;
        const g = c.getContext('2d'); g.drawImage(im,0,0);
        const d = g.getImageData(Math.floor(im.width/2), Math.floor(im.height/2), 1, 1).data;
        res([im.width, im.height, d[0], d[1], d[2]]); }}; im.src = 'data:image/{fmt};base64,{b64}'; }})"""
    return await tab.evaluate(js, await_promise=True)

async def main():
    browser = await zd.start(headless=True)
    try:
        tab = await browser.get((HERE / "page.html").as_uri())
        await tab.sleep(0.5)
        mir = await tab.select("#mir")
        print("mir pos", await mir.get_position())
        t0 = time.monotonic()
        task = asyncio.ensure_future(mir.screenshot_b64(format="png"))
        # meanwhile do other traffic: positive screenshot, scrolling, evaluate, navigation within 60s
        await asyncio.sleep(5)
        plain = await tab.select("#plain")
        r = await asyncio.wait_for(plain.screenshot_b64(format="png"), 15)
        print("plain screenshot meanwhile works; pixel", await pixel(tab, r), "mir task done?", task.done())
        await tab.evaluate("window.scrollTo(0,500)"); await asyncio.sleep(2)
        await tab.evaluate("window.scrollTo(0,0)")
        done, _ = await asyncio.wait([task], timeout=50)
        print(f"after {time.monotonic()-t0:.0f}s mir task done? {task.done()}")
        if not done:
            task.print_stack(limit=3, file=sys.stdout)
            # reload page: does the pending reply ever come?
            await tab.reload()
            await asyncio.sleep(3)
            print("after reload mir task done?", task.done(), task.exception() if task.done() else "")
            task.cancel()
        # pending transactions on the tab mapper
        print("mapper pending count:", len(getattr(tab, "mapper", {})))
        # A8.2 scrolled with pixel check
        tab = await tab.get((HERE / "page.html").as_uri())
        await tab.sleep(0.5)
        blue = await tab.select("#blue")
        r = await asyncio.wait_for(blue.screenshot_b64(format="png"), 15)
        print("blue unscrolled pos", await blue.get_position(), "pixel", await pixel(tab, r))
        await tab.evaluate("window.scrollTo(0, 1500)"); await tab.sleep(0.3)
        r = await asyncio.wait_for(blue.screenshot_b64(format="png"), 15)
        print("blue scrolled scrollY", await tab.evaluate("window.scrollY"), "pos", await blue.get_position(), "pixel", await pixel(tab, r))
        # also check: scroll_into_view then screenshot (common usage)
        await tab.evaluate("window.scrollTo(0, 0)"); await tab.sleep(0.3)
        await blue.scroll_into_view(); await tab.sleep(0.3)
        r = await asyncio.wait_for(blue.screenshot_b64(format="png"), 15)
        print("after scroll_into_view scrollY", await tab.evaluate("window.scrollY"), "pos", await blue.get_position(), "pixel", await pixel(tab, r))
        # element below fold without scrolling
        await tab.evaluate("window.scrollTo(0, 0)"); await tab.sleep(0.3)
        r = await asyncio.wait_for(blue.screenshot_b64(format="png"), 15)
        print("below-fold unscrolled pixel", await pixel(tab, r))
    finally:
        await browser.stop()

asyncio.run(main())
