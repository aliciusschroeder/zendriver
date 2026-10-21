import asyncio, base64, os, sys, pathlib, time
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
        r = await tab.send(cdp.page.capture_screenshot("png", clip=cdp.page.Viewport(100, 30, 100, 40, 1), capture_beyond_viewport=True))
        w, h, px = decode_png(base64.b64decode(r))
        print("control mir region before", w, h, px(w//2, h//2))
        await tab.evaluate("document.getElementById('rot').style.transform='rotate(90deg)'")
        rot = await tab.select("#rot")
        print("rot90 Position", await rot.get_position())
        mir = await tab.select("#mir")
        t0 = time.monotonic()
        t = asyncio.ensure_future(mir.screenshot_b64(format="png"))
        done, pending = await asyncio.wait([t], timeout=60)
        print("mir after %.1fs pending=%s" % (time.monotonic() - t0, bool(pending)))
        if pending:
            t.cancel()
        # tab still usable?
        print("evaluate after:", await asyncio.wait_for(tab.evaluate("1+1"), 10))
        t = asyncio.ensure_future(rot.screenshot_b64(format="png"))
        done, pending = await asyncio.wait([t], timeout=15)
        print("rot90 pending=%s" % bool(pending), (t.exception() if done else ""))
        if pending: t.cancel()
    finally:
        await browser.stop()
        print("browser stopped")

asyncio.run(asyncio.wait_for(main(), 110))
