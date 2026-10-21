import asyncio, base64, io, sys, pathlib
import zendriver as zd
from zendriver import cdp
print("zendriver from", zd.__file__, sys.version.split()[0])
HERE = pathlib.Path(__file__).parent

def center_pixel(b64):
    data = base64.b64decode(b64)
    try:
        from PIL import Image
        im = Image.open(io.BytesIO(data)).convert("RGB")
        return im.size, im.getpixel((im.size[0]//2, im.size[1]//2))
    except ImportError:
        return len(data), None

async def timed(label, coro, t=15):
    task = asyncio.ensure_future(coro)
    done, pending = await asyncio.wait([task], timeout=t)
    if pending:
        print(f"[{label}] STILL PENDING after {t}s; stack:")
        task.print_stack(limit=6, file=sys.stdout)
        task.cancel()
        try:
            await task
        except BaseException as e:
            print(f"[{label}] cancelled: {type(e).__name__}")
        return None
    try:
        r = task.result()
        print(f"[{label}] OK ->", (r[:40] + '...') if isinstance(r, str) else r)
        return r
    except Exception as e:
        print(f"[{label}] EXC {type(e).__name__}: {str(e)[:250]}")
        return None

async def main():
    browser = await zd.start(headless=True)
    try:
        tab = await browser.get((HERE / "page.html").as_uri())
        await tab.sleep(0.5)
        for sel in ["#plain", "#mir", "#r180", "#r90", "#r45"]:
            el = await tab.select(sel)
            quads = await tab.send(cdp.dom.get_content_quads(backend_node_id=el.backend_node_id))
            pos = await el.get_position()
            print(sel, "quad", [round(q) for q in quads[0]], "pos", pos)
            r = await timed(f"{sel} screenshot_b64 png", el.screenshot_b64(format="png"), 12)
            if r:
                print("   center/size", center_pixel(r))
        # direct CDP with negative width, independent of zendriver Position
        for vp in [dict(x=150,y=50,width=-100,height=40), dict(x=150,y=50,width=0,height=40), dict(x=150,y=50,width=100,height=-40)]:
            await timed(f"raw captureScreenshot {vp}", tab.send(cdp.page.capture_screenshot("png", clip=cdp.page.Viewport(scale=1, **vp), capture_beyond_viewport=True)), 12)
            await timed(f"raw captureScreenshot cbv=False {vp}", tab.send(cdp.page.capture_screenshot("png", clip=cdp.page.Viewport(scale=1, **vp), capture_beyond_viewport=False)), 12)
        # after hang: does the tab still respond?
        print("tab still alive? ", await asyncio.wait_for(tab.evaluate("1+1"), 10))
        # A8.2 scrolled
        blue = await tab.select("#blue")
        r = await timed("blue unscrolled", blue.screenshot_b64(format="png"))
        if r: print("   center", center_pixel(r))
        await tab.evaluate("window.scrollTo(0, 1500)")
        await tab.sleep(0.3)
        print("scrollY", await tab.evaluate("window.scrollY"), "pos", await blue.get_position())
        r = await timed("blue scrolled", blue.screenshot_b64(format="png"))
        if r: print("   center", center_pixel(r))
        # A8.11 jpg
        plain = await tab.select("#plain")
        await tab.evaluate("window.scrollTo(0, 0)")
        await timed("save_screenshot jpg", plain.save_screenshot(str(HERE / "x.jpg"), format="jpg"))
        await timed("save_screenshot auto jpg", plain.save_screenshot(format="jpg"))
        await timed("tab.save_screenshot jpg", tab.save_screenshot(str(HERE / "t.jpg"), format="jpg"))
    finally:
        await browser.stop()

asyncio.run(main())
