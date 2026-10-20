import asyncio
import zendriver as zd
from zendriver.core.connection import ProtocolException

async def main():
    browser = await zd.start(headless=True)
    try:
        tab = await browser.get("about:blank")
        try:
            await tab.send(zd.cdp.page.navigate(url=None))
        except ProtocolException as e:
            print("str(e):", repr(str(e)))
            print("e.args[0]:", e.args[0])
        try:
            await tab.send(zd.cdp.dom.get_box_model(node_id=zd.cdp.dom.NodeId(999999)))
        except ProtocolException as e:
            print("str(e):", repr(str(e)))
            print("e.args[0]:", e.args[0])
    finally:
        await browser.stop()

asyncio.run(main())
