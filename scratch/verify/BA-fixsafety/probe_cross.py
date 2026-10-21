"""cross-group checks: R17 prototype with autodiscover off; R25 prototype close-then-get."""

import asyncio
import time

import zendriver as zd
from zendriver import cdp

print("zendriver from", zd.__file__)


async def main():
    cfg = zd.Config(headless=True)
    cfg.autodiscover_targets = False
    browser = await zd.Browser.create(cfg)
    try:
        n0 = len([t for t in await browser._get_targets() if t.type_ == "page"])
        t = time.monotonic()
        try:
            tab = await asyncio.wait_for(browser.get("data:text/html,x", new_tab=True, timeout=2), 20)
            print("get(new_tab): OK", tab)
        except Exception as e:
            print(f"get(new_tab): {type(e).__name__} after {time.monotonic() - t:.1f}s")
        await asyncio.sleep(0.5)
        n1 = len([t for t in await browser._get_targets() if t.type_ == "page"])
        print("page targets before/after:", n0, n1)
        await browser.update_targets()
        first = browser.tabs[0]
        await asyncio.wait_for(first.close(), 15)
        try:
            await asyncio.wait_for(browser.get("data:text/html,y", timeout=2), 20)
            print("get after close without update_targets: OK")
        except Exception as e:
            print("get after close without update_targets:", type(e).__name__, str(e).splitlines()[0])
    finally:
        await browser.stop()


asyncio.run(main())
