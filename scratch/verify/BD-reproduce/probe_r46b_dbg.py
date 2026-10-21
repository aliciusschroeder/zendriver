import asyncio, os, sys
sys.path.insert(0, os.path.dirname(__file__))
import zendriver as zd
from zendriver import cdp
from zendriver.cdp.fetch import RequestStage
from zendriver.cdp.network import ResourceType
import probe_r46b_srv as S
async def main():
    browser = await zd.start(headless=True)
    try:
        tab = browser.main_tab
        await tab.get(S.BASE + "/blank")
        async with tab.intercept("*b.json*", RequestStage.REQUEST, ResourceType.XHR) as b:
            print("handlers:", {k.__name__: len(v) for k, v in tab.handlers.items() if isinstance(k, type)})
            await tab.get(S.BASE + "/page")
            await asyncio.sleep(2)
            print("future done?", b.response_future.done())
            print("window:", await tab.evaluate("[window.__a, window.__b, location.href]"))
    finally:
        await browser.stop(); print("stopped")
asyncio.run(asyncio.wait_for(main(), 60))
