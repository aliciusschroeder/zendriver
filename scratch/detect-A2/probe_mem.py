import asyncio
import zendriver as zd
from zendriver import cdp
import logging

async def main():
    browser = await zd.start(headless=True)
    try:
        tab = await browser.get("about:blank")
        for fn in (cdp.memory.get_sampling_profile, cdp.runtime.get_heap_usage):
            try:
                r = await asyncio.wait_for(tab.send(fn()), 5)
                print("ok", fn.__name__, str(r)[:80])
            except asyncio.TimeoutError:
                print("HUNG", fn.__name__, "mapper", list(tab.mapper), "inbox", tab._inbox.qsize())
    finally:
        await browser.stop()

asyncio.run(asyncio.wait_for(main(), 50))
