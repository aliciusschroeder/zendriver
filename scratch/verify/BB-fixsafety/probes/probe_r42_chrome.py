import asyncio, json
import zendriver as zd
from zendriver import cdp
from zendriver.core.connection import ProtocolException
print("ZENDRIVER IMPORTED FROM", zd.__file__)
async def main():
    browser = await zd.start(headless=True)
    try:
        tab = browser.main_tab
        await tab.get("about:blank")
        frames = []
        orig = tab._session_parent.websocket.recv
        try:
            await asyncio.wait_for(tab.send(cdp.emulation.set_device_metrics_override(width=100, height=100, device_scale_factor=float("nan"), mobile=False)), 4)
            print("A1.3 NaN send returned")
        except asyncio.TimeoutError:
            print("A1.3 NaN send HUNG 4s; pending mapper ids:", list(tab.mapper))
        except Exception as e:
            print("A1.3 NaN send raised", type(e).__name__, e)
        print("A1.3 still usable:", await asyncio.wait_for(tab.evaluate("2+2"), 5))
        try:
            await tab.send(cdp.page.navigate(url=None))
        except ProtocolException as e:
            print("A1.8 str(e):", repr(str(e)))
            print("A1.8 args[0]:", e.args[0])
    finally:
        await browser.stop()
asyncio.run(main())
