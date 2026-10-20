import asyncio, sys, logging
import zendriver as zd
from zendriver import cdp
sys.path.insert(0, "/home/user/zendriver")
from tests.sample_data import sample_file

async def main():
    browser = await zd.start(headless=True)
    try:
        tab = await browser.get(sample_file("groceries.html"))
        await tab.wait_for_ready_state("complete")
        # 1. Tab.__call__(text=...)
        try:
            el = await asyncio.wait_for(tab(text="Apples", timeout=1), 10)
            print("call(text=Apples) ->", el)
        except Exception as e:
            print("call(text=Apples) raised", type(e).__name__, e)
        try:
            el = await asyncio.wait_for(tab(selector="li", timeout=1), 10)
            print("call(selector=li) ->", el.tag if el else el, repr(el.text_all)[:80])
        except Exception as e:
            print("call(selector=li) raised", type(e).__name__, e)
        el = await tab.wait_for(text="Apples", timeout=1)
        print("wait_for(text=Apples) ->", el.tag, el.text)
    finally:
        await browser.stop()

asyncio.run(asyncio.wait_for(main(), 50))
