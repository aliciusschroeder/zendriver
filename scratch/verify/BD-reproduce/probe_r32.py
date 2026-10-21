import asyncio, base64, os, sys, pathlib
sys.path.insert(0, os.path.dirname(__file__))
import zendriver as zd
from zendriver import cdp
from pngdec import decode_png
print("zendriver from", zd.__file__, "python", sys.version.split()[0])
D = os.path.dirname(os.path.abspath(__file__))
URL = pathlib.Path(D, "r32.html").as_uri()

async def main():
    browser = await zd.start(headless=True, browser_args=["--window-size=800,600"])
    try:
        tab = await browser.get(URL)
        await tab.sleep(0.5)
        # --- baseline: plain element screenshot
        plain = await tab.select("#plain")
        print("plain pos", await plain.get_position())
        data = await asyncio.wait_for(plain.screenshot_b64(format="png"), 20)
        w, h, px = decode_png(base64.b64decode(data))
        print("plain screenshot", w, h, "centre", px(w//2, h//2))

        # --- A8.1 mirrored / rotated
        for sel in ("#mir", "#rot"):
            el = await tab.select(sel)
            quads = await tab.send(cdp.dom.get_content_quads(backend_node_id=el.backend_node_id))
            print(sel, "raw quad", quads[0])
            pos = await el.get_position()
            print(sel, "Position", pos, "viewport", pos.to_viewport(1.0).to_json())
            t = asyncio.ensure_future(el.screenshot_b64(format="png"))
            done, pending = await asyncio.wait([t], timeout=20)
            if pending:
                print(sel, "STILL PENDING after 20s; stack:")
                t.print_stack(file=sys.stdout)
                t.cancel()
                try:
                    await t
                except BaseException as e:
                    print(sel, "cancelled:", type(e).__name__)
            else:
                try:
                    r = t.result()
                    print(sel, "returned len", len(r))
                except Exception as e:
                    print(sel, "raised", type(e).__name__, str(e)[:200])
            # control: positive-width clip at same location
            vp = pos.to_viewport(1.0)
            fixed = cdp.page.Viewport(x=min(pos.left, pos.right), y=min(pos.top, pos.bottom), width=abs(pos.width), height=abs(pos.height), scale=1)
            try:
                r = await asyncio.wait_for(tab.send(cdp.page.capture_screenshot("png", clip=fixed, capture_beyond_viewport=True)), 10)
                w, h, px = decode_png(base64.b64decode(r))
                print(sel, "control positive clip ok", w, h, "centre", px(w//2, h//2))
            except Exception as e:
                print(sel, "control raised", type(e).__name__, e)

        # --- A8.2 scrolled page
        blue = await tab.select("#blue")
        await tab.evaluate("window.scrollTo(0,0)")
        await tab.sleep(0.3)
        data = await asyncio.wait_for(blue.screenshot_b64(format="png"), 20)
        w, h, px = decode_png(base64.b64decode(data))
        print("unscrolled blue pos", await blue.get_position(), "shot", w, h, "centre", px(w//2, h//2))
        await tab.evaluate("window.scrollTo(0,1100)")
        await tab.sleep(0.3)
        print("scrollY", await tab.evaluate("window.scrollY"))
        data = await asyncio.wait_for(blue.screenshot_b64(format="png"), 20)
        w, h, px = decode_png(base64.b64decode(data))
        print("scrolled blue pos", await blue.get_position(), "shot", w, h, "centre", px(w//2, h//2))

        # --- A8.11 jpg
        await tab.evaluate("window.scrollTo(0,0)")
        out = os.path.join(D, "out_r32.jpg")
        try:
            p = await asyncio.wait_for(plain.save_screenshot(out, format="jpg"), 20)
            print("save_screenshot jpg ok", p, os.path.getsize(p))
        except Exception as e:
            print("save_screenshot jpg raised", type(e).__name__, str(e)[:300])
        try:
            p = await asyncio.wait_for(plain.save_screenshot("auto", format="jpg"), 20)
            print("save_screenshot auto jpg ok", p)
        except Exception as e:
            print("save_screenshot auto jpg raised", type(e).__name__, str(e)[:300])
        # contrast: tab version
        try:
            p = await asyncio.wait_for(tab.save_screenshot(os.path.join(D, "tab_r32.jpg"), format="jpg"), 20)
            print("tab.save_screenshot jpg ok", p)
        except Exception as e:
            print("tab.save_screenshot jpg raised", type(e).__name__, str(e)[:200])
        if os.path.exists(out): os.remove(out)
        for f in os.listdir(D):
            if f.endswith('.jpg'): os.remove(os.path.join(D, f))
    finally:
        await browser.stop()
        print("browser stopped")

asyncio.run(asyncio.wait_for(main(), 110))
