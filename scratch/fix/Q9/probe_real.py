import asyncio, json
import zendriver as zd
from zendriver import cdp
from zendriver.core.connection import Connection, ProtocolException
print("zendriver from", zd.__file__, "| Tab.__aexit__ is Connection.__aexit__:", zd.Tab.__aexit__ is Connection.__aexit__)

async def main():
    browser = await zd.start(headless=True)
    try:
        tab = browser.main_tab
        try:
            async with tab:
                await tab.send(cdp.dom.resolve_node(node_id=cdp.dom.NodeId(999999)))
        except Exception as e:
            print("tab/protocol:", type(e).__name__, "code=", getattr(e, "code", "n/a"))
        tab2 = await browser.get("about:blank", new_tab=True)
        try:
            async with tab2:
                json.loads("{bad")
        except Exception as e:
            print("tab/json:", type(e).__name__, str(e)[:70])
        try:
            async with browser:
                json.loads("{bad")
        except Exception as e:
            print("browser/json:", type(e).__name__, str(e)[:70])
        # browser still usable after async with tab detach?
        t3 = await browser.get("about:blank", new_tab=True)
        print("browser usable after:", (await t3.evaluate("1+1")))
    finally:
        await browser.stop()

asyncio.run(asyncio.wait_for(main(), 60))
