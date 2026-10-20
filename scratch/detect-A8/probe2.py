import asyncio, pathlib, base64, zlib, struct, io
import zendriver as zd
from zendriver import cdp

PAGE = pathlib.Path(__file__).parent / "page2.html"

def png_center_pixel(b64):
    import minipng; size, px = minipng.decode(b64); return size, px(size[0]//2, size[1]//2)
def _old(b64):
    from PIL import Image
    im = Image.open(io.BytesIO(base64.b64decode(b64))).convert("RGB")
    return im.size, im.getpixel((im.size[0]//2, im.size[1]//2))

async def step(name, coro):
    try:
        r = await asyncio.wait_for(coro, 15)
        print(f"[{name}] OK ->", repr(r)[:150])
        return r
    except Exception as e:
        print(f"[{name}] EXC {type(e).__name__}: {str(e)[:250]}")

async def main():
    browser = await zd.start(headless=True)
    try:
        tab = await browser.get(PAGE.as_uri())
        await tab.sleep(0.5)
        blue = await tab.query_selector("#blue")
        b64 = await step("F shot unscrolled", blue.screenshot_b64(format="png"))
        if b64: print("  size/center pixel:", png_center_pixel(b64))
        await tab.evaluate("window.scrollTo(0, 1100)")
        await tab.sleep(0.3)
        print("  scrollY =", await tab.evaluate("window.scrollY"))
        print("  pos =", await blue.get_position())
        b64 = await step("F shot scrolled", blue.screenshot_b64(format="png"))
        if b64: print("  size/center pixel:", png_center_pixel(b64))
        await tab.evaluate("window.scrollTo(0, 0)")
        await tab.sleep(0.3)
        mir = await tab.query_selector("#mir")
        print("  mir pos:", await mir.get_position())
        b64 = await step("S shot mirrored", mir.screenshot_b64(format="png"))
        if b64: print("  size/center pixel:", png_center_pixel(b64))
        rot = await tab.query_selector("#rot")
        p = await rot.get_position()
        print("  rot pos:", p, "center", p.center, "quad", list(p))
        await step("S mouse_click rotated", rot.mouse_click())
        await tab.sleep(0.2)
        print("  rotClicked =", await tab.evaluate("window.rotClicked"))
        # jpg
        r = await step("R save_screenshot jpg", blue.save_screenshot(str(pathlib.Path(__file__).parent / "x.jpg"), format="jpg"))
        # class attr
        print("[V] mir.get('class') =", mir.get("class"), " attrs keys:", list(mir.attrs.keys()))
        # set_text via element query
        body = await tab.query_selector("body")
        txt = await body.query_selector("#txt")
        await step("N set_text", txt.set_text("world"))
        print("  txt text:", await tab.evaluate("document.getElementById('txt').textContent"))
    finally:
        await browser.stop()

asyncio.run(main())
