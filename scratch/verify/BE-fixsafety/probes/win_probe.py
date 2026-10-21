import asyncio
import zendriver
from zendriver import cdp
print("zendriver from", zendriver.__file__)

async def show(tab, label):
    _, b = await tab.get_window()
    print(f"{label}: state={b.window_state.value if b.window_state else None} l={b.left} t={b.top} w={b.width} h={b.height}")

async def main():
    browser = await zendriver.start(headless=True)
    try:
        tab = browser.main_tab
        await show(tab, "initial")
        for st in ["maximize", "minimize", "fullscreen"]:
            await tab.set_window_size(10, 10, 700, 500)
            await getattr(tab, st)()
            await show(tab, f"after {st}")
            await tab.set_window_size(200, 100, 900, 700)
            await show(tab, f"  set_window_size(200,100,900,700) after {st}")
        # A6.7
        await tab.set_window_size(100, 50, 800, 600)
        await show(tab, "A sized")
        await tab.maximize()
        await show(tab, "A maximized")
        wid, _ = await tab.get_window()
        await tab.send(cdp.browser.set_window_bounds(wid, cdp.browser.Bounds(window_state=cdp.browser.WindowState.NORMAL)))
        await show(tab, "A plain restore")
        await tab.set_window_size(100, 50, 800, 600)
        await tab.send(cdp.browser.set_window_bounds(wid, cdp.browser.Bounds(window_state=cdp.browser.WindowState.MAXIMIZED)))
        await show(tab, "B raw maximized")
        await tab.send(cdp.browser.set_window_bounds(wid, cdp.browser.Bounds(window_state=cdp.browser.WindowState.NORMAL)))
        await show(tab, "B plain restore")
        # raw: maximize -> minimize directly?
        for a, b in [("MAXIMIZED","MINIMIZED"),("MINIMIZED","MAXIMIZED"),("FULLSCREEN","MAXIMIZED"),("FULLSCREEN","MINIMIZED"),("MINIMIZED","FULLSCREEN"), ("MAXIMIZED","FULLSCREEN")]:
            await tab.send(cdp.browser.set_window_bounds(wid, cdp.browser.Bounds(window_state=cdp.browser.WindowState.NORMAL)))
            await tab.send(cdp.browser.set_window_bounds(wid, cdp.browser.Bounds(window_state=getattr(cdp.browser.WindowState,a))))
            try:
                await tab.send(cdp.browser.set_window_bounds(wid, cdp.browser.Bounds(window_state=getattr(cdp.browser.WindowState,b))))
                await show(tab, f"raw {a}->{b} OK")
            except Exception as e:
                print(f"raw {a}->{b} EXC", str(e).splitlines()[0])
    finally:
        await browser.stop()

asyncio.run(asyncio.wait_for(main(), 90))
