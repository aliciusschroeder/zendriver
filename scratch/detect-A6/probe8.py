import asyncio, pathlib, traceback, time, sys
import zendriver as zd
from zendriver import cdp
SITE = pathlib.Path(__file__).parent / "site"
def url(n): return (SITE / n).as_uri()
async def main():
    browser = await zd.start(headless=True)
    try:
        tab = await browser.get(url("long.html"))
        await tab.wait_for_ready_state("complete")
        wid, b = await tab.get_window()
        print("bounds", b, "inner", await tab.evaluate("[innerWidth, innerHeight]"))
        t0=time.monotonic(); await tab.scroll_down(50); print("scroll_down took", round(time.monotonic()-t0,2))
        await asyncio.sleep(0.5)
        print("scrollY after scroll_down(50):", await tab.evaluate("window.scrollY"))
        await tab.scroll_down(200); await asyncio.sleep(0.5)
        print("scrollY after scroll_down(200):", await tab.evaluate("window.scrollY"))
        await tab.scroll_up(100); await asyncio.sleep(0.5)
        print("scrollY after scroll_up(100):", await tab.evaluate("window.scrollY"))
        # same gesture at center
        await tab.send(cdp.input_.synthesize_scroll_gesture(x=100, y=100, y_distance=-300, prevent_fling=True, speed=800))
        await asyncio.sleep(0.5)
        print("scrollY after manual gesture at 100,100:", await tab.evaluate("window.scrollY"))
    finally:
        await browser.stop()
asyncio.run(main())
