import asyncio, pathlib, time
import zendriver as zd
from zendriver import cdp
SITE = pathlib.Path(__file__).parent / "site"
def url(n): return (SITE / n).as_uri()
async def win(tab, label):
    wid, b = await tab.get_window()
    print(f"   {label}: state={b.window_state.value} l={b.left} t={b.top} w={b.width} h={b.height}")
    return wid
async def main():
    browser = await zd.start(headless=True)
    try:
        tab = await browser.get(url("simple.html"))
        # 10: clobber
        await tab.set_window_size(100, 50, 800, 600); wid = await win(tab, "A sized")
        await tab.maximize(); await win(tab, "A maximized")
        await tab.send(cdp.browser.set_window_bounds(wid, cdp.browser.Bounds(window_state=cdp.browser.WindowState.NORMAL)))
        await win(tab, "A plain restore (no bounds)")
        # control: raw maximize without zendriver's pre-normalisation
        await tab.set_window_size(100, 50, 800, 600); await win(tab, "B sized")
        await tab.send(cdp.browser.set_window_bounds(wid, cdp.browser.Bounds(window_state=cdp.browser.WindowState.MAXIMIZED)))
        await win(tab, "B raw maximize")
        await tab.send(cdp.browser.set_window_bounds(wid, cdp.browser.Bounds(window_state=cdp.browser.WindowState.NORMAL)))
        await win(tab, "B plain restore")
        # 9: set_window_size from non-normal states
        for st in ["maximize", "minimize", "fullscreen"]:
            await tab.set_window_size(100, 50, 800, 600)
            await getattr(tab, st)()
            await tab.set_window_size(200, 100, 900, 700)
            await win(tab, f"C set_window_size(200,100,900,700) after {st}")
    finally:
        await browser.stop()
asyncio.run(main())
