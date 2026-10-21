"""SEED-C3 with real Chromium: timed-out evaluate of a never-settling promise; is the entry ever released?"""
import asyncio, sys, tracemalloc
import zendriver
from zendriver import cdp
print("zendriver from", zendriver.__file__, "python", sys.version.split()[0])

async def main():
    browser = await zendriver.start(headless=True)
    try:
        tab = await browser.get("data:text/html,<p>a</p>")
        await tab.evaluate("1")
        tracemalloc.start()
        snap0 = tracemalloc.take_snapshot()
        n = 200
        for _ in range(n):
            try:
                await asyncio.wait_for(tab.evaluate("new Promise(() => {})", await_promise=True), 0.02)
            except asyncio.TimeoutError:
                pass
        await asyncio.sleep(0.5)
        snap1 = tracemalloc.take_snapshot()
        diff = sum(s.size_diff for s in snap1.compare_to(snap0, "filename"))
        print(f"mapper size after {n} timed-out never-settling evaluates: {len(tab.mapper)}; ~{diff/n:.0f} bytes/entry (tracemalloc)")
        tracemalloc.stop()
        await tab.evaluate("1")
        print("mapper size after an unrelated command:", len(tab.mapper))
        await tab.send(cdp.page.navigate("data:text/html,<p>b</p>"))
        await asyncio.sleep(1.0)
        print("mapper size 1s after navigating the page:", len(tab.mapper))
        # same for reload of a page with the pending promise
        for _ in range(3):
            try:
                await asyncio.wait_for(tab.evaluate("new Promise(() => {})", await_promise=True), 0.05)
            except asyncio.TimeoutError:
                pass
        print("mapper size after 3 more:", len(tab.mapper))
        await tab.reload()
        await asyncio.sleep(1.0)
        print("mapper size 1s after reload:", len(tab.mapper))
    finally:
        await browser.stop()
asyncio.run(main())
