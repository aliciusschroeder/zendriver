import asyncio, sys
import zendriver
from zendriver import cdp
print("zendriver:", zendriver.__file__)

def fmt(b):
    return f"state={b.window_state.value if b.window_state else None} l={b.left} t={b.top} w={b.width} h={b.height}"

async def main():
    browser = await zendriver.start(headless=True)
    try:
        tab = browser.main_tab
        wid, b = await tab.get_window(); print("initial:", fmt(b))
        # A6.6: set_window_size after non-normal states
        for name in ("maximize", "minimize", "fullscreen"):
            await tab.set_window_size(10, 10, 1000, 800)
            await getattr(tab, name)()
            await asyncio.sleep(0.5)
            _, b = await tab.get_window(); print(f"A6.6 after {name}: {fmt(b)}")
            await tab.set_window_size(200, 100, 900, 700)
            await asyncio.sleep(0.5)
            _, b = await tab.get_window(); print(f"A6.6   set_window_size(200,100,900,700) after {name}: {fmt(b)}")
        # A6.7: maximize loses restore geometry
        await tab.set_window_size(100, 50, 800, 600); await asyncio.sleep(0.5)
        _, b = await tab.get_window(); print("A6.7 sized:", fmt(b))
        await tab.maximize(); await asyncio.sleep(0.5)
        _, b = await tab.get_window(); print("A6.7 after tab.maximize():", fmt(b))
        await tab.send(cdp.browser.set_window_bounds(wid, cdp.browser.Bounds(window_state=cdp.browser.WindowState.NORMAL))); await asyncio.sleep(0.5)
        _, b = await tab.get_window(); print("A6.7 plain restore:", fmt(b))
        # control: raw maximize
        await tab.set_window_size(100, 50, 800, 600); await asyncio.sleep(0.5)
        await tab.send(cdp.browser.set_window_bounds(wid, cdp.browser.Bounds(window_state=cdp.browser.WindowState.MAXIMIZED))); await asyncio.sleep(0.5)
        _, b = await tab.get_window(); print("A6.7 control raw maximize:", fmt(b))
        await tab.send(cdp.browser.set_window_bounds(wid, cdp.browser.Bounds(window_state=cdp.browser.WindowState.NORMAL))); await asyncio.sleep(0.5)
        _, b = await tab.get_window(); print("A6.7 control plain restore:", fmt(b))
        # A6.7 intermediate: record what maximize() sends
        sent = []
        orig = tab.send
        async def spy(cmd, *a, **k):
            gen = cmd
            res = await orig(cmd, *a, **k)
            return res
        # inspect via bounds right after the inner normal step: patch instance send to log set_window_bounds params
        async def logging_send(cmd, *a, **k):
            # peek at the generator's first yielded request without consuming it twice
            req = cmd.send(None)
            sent.append(req)
            async def replay():
                pass
            # re-wrap: build a generator that yields req then delegates
            def regen():
                resp = yield req
                try:
                    cmd.send(resp)
                except StopIteration as e:
                    return e.value
            return await orig(regen(), *a, **k)
        tab.send = logging_send
        await tab.set_window_size(100, 50, 800, 600)
        await tab.maximize()
        del tab.send
        for r in sent:
            if r["method"] == "Browser.setWindowBounds":
                print("A6.7 sent:", r["params"])
    finally:
        await browser.stop()

asyncio.run(asyncio.wait_for(main(), 100))
