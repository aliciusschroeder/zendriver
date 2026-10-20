import asyncio, sys
import zendriver as zd
from zendriver import cdp

async def main():
    browser = await zd.start(headless=True)
    try:
        tab = await browser.get("about:blank")
        for fn in (cdp.page.get_frame_tree, cdp.page.get_layout_metrics, cdp.runtime.get_heap_usage, cdp.performance.get_metrics):
            try:
                r = await asyncio.wait_for(tab.send(fn()), 5)
                print("ok", fn.__name__, str(r)[:80])
            except asyncio.TimeoutError:
                print("HUNG", fn.__name__, "tab listener", tab.listener.running, "browser listener", browser.connection.listener.running, "mapper", list(tab.mapper))
    finally:
        await browser.stop()

asyncio.run(asyncio.wait_for(main(), 50))
