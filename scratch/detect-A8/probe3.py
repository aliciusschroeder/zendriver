import asyncio, pathlib, time
import zendriver as zd
from zendriver import cdp
PAGE = pathlib.Path(__file__).parent / "page2.html"
async def main():
    browser = await zd.start(headless=True)
    try:
        tab = await browser.get(PAGE.as_uri())
        await tab.sleep(0.5)
        mir = await tab.query_selector("#mir")
        t = time.monotonic()
        task = asyncio.ensure_future(mir.screenshot_b64(format="png"))
        done, _ = await asyncio.wait([task], timeout=45)
        if not done:
            print("still pending after %.1fs; stack:" % (time.monotonic()-t))
            task.print_stack(limit=6)
            task.cancel()
        else:
            try: print("result", repr(task.result())[:80])
            except Exception as e: print("exc", type(e).__name__, e)
        # Is the tab still usable afterwards?
        try:
            r = await asyncio.wait_for(tab.evaluate("1+1"), 10)
            print("tab.evaluate after:", r)
        except Exception as e:
            print("tab.evaluate after EXC", type(e).__name__, e)
        # direct call with positive width at same spot
        try:
            r = await asyncio.wait_for(tab.send(cdp.page.capture_screenshot("png", clip=cdp.page.Viewport(50, 50, 100, 40, 1), capture_beyond_viewport=True)), 10)
            print("positive width capture ok len", len(r))
        except Exception as e:
            print("positive width capture EXC", type(e).__name__, e)
    finally:
        await asyncio.wait_for(browser.stop(), 20)
asyncio.run(main())
