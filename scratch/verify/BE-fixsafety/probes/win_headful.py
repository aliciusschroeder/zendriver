import asyncio, sys
import zendriver
from zendriver import cdp
print("zendriver from", zendriver.__file__)
async def show(tab, label):
    _, b = await tab.get_window()
    print(f"{label}: state={b.window_state.value} l={b.left} t={b.top} w={b.width} h={b.height}")
async def main():
    browser = await zendriver.start(headless=False)
    try:
        tab = browser.main_tab
        await show(tab, "initial")
        for st in ["maximize", "minimize", "fullscreen"]:
            await tab.set_window_size(10, 10, 700, 500)
            await getattr(tab, st)(); await asyncio.sleep(0.5)
            await show(tab, f"after {st}")
            await tab.set_window_size(200, 100, 900, 700); await asyncio.sleep(0.5)
            await show(tab, f"  set_window_size(200,100,900,700) after {st}")
    finally:
        await browser.stop()
asyncio.run(asyncio.wait_for(main(), 90))
