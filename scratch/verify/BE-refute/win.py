import asyncio, sys, os
import zendriver as zd
from zendriver import cdp
print("zendriver from", zd.__file__)
HEADLESS = sys.argv[1] == "headless"
async def main():
    browser = await zd.start(headless=HEADLESS)
    try:
        tab = browser.main_tab
        async def show(label):
            await asyncio.sleep(0.8)
            _, b = await tab.get_window()
            print(f"  {label}: state={b.window_state.value if b.window_state else None} l={b.left} t={b.top} w={b.width} h={b.height}")
        print("A6.6: resize while non-normal")
        for st in ["maximize", "minimize", "fullscreen"]:
            await tab.set_window_size(50, 60, 800, 600); await show("start")
            await tab.set_window_state(state=st); await show(st)
            await tab.set_window_size(200, 100, 900, 700); await show(f"set_window_size(200,100,900,700) after {st}")
        print("A6.7: maximize loses restore geometry")
        await tab.set_window_size(100, 50, 800, 600); await show("sized")
        await tab.maximize(); await show("tab.maximize()")
        wid, _ = await tab.get_window()
        await tab.send(cdp.browser.set_window_bounds(wid, cdp.browser.Bounds(window_state=cdp.browser.WindowState.NORMAL))); await show("plain restore")
        print("control: raw maximize")
        await tab.set_window_size(100, 50, 800, 600); await show("sized")
        await tab.send(cdp.browser.set_window_bounds(wid, cdp.browser.Bounds(window_state=cdp.browser.WindowState.MAXIMIZED))); await show("raw maximize")
        await tab.send(cdp.browser.set_window_bounds(wid, cdp.browser.Bounds(window_state=cdp.browser.WindowState.NORMAL))); await show("plain restore")
        print("control: raw resize while maximized (does Chrome itself drop bounds?)")
        await tab.send(cdp.browser.set_window_bounds(wid, cdp.browser.Bounds(window_state=cdp.browser.WindowState.MAXIMIZED))); await show("raw maximize")
        try:
            await tab.send(cdp.browser.set_window_bounds(wid, cdp.browser.Bounds(left=200, top=100, width=900, height=700))); await show("raw bounds w/o state while maximized")
        except Exception as e:
            print("  raw bounds w/o state while maximized EXC", str(e).splitlines()[0])
    finally:
        await browser.stop()
asyncio.run(asyncio.wait_for(main(), 100))
