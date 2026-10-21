import asyncio
import sys

import zendriver as zd
from zendriver import cdp
from zendriver.core.connection import ProtocolException

print("zendriver from", zd.__file__, sys.version.split()[0])


async def main():
    browser = await zd.start(headless=True)
    try:
        tab = await browser.get("about:blank")
        # capture raw frames on the browser connection (flat sessions: tab frames
        # carry sessionId, an unparseable frame cannot be routed back)
        raw = []
        bc = browser.connection
        orig = bc._receive_message

        async def wrapped():
            m = await orig()
            if m is not None and "id" not in m and "error" in m:
                raw.append(("browser-conn", m))
            return m

        bc._receive_message = wrapped
        torig = tab._receive_message

        async def twrapped():
            m = await torig()
            if m is not None and "id" not in m and "error" in m:
                raw.append(("tab", m))
            return m

        tab._receive_message = twrapped

        print("tab session_id:", tab.session_id)
        for label, cmd in [
            ("nan dsf", cdp.emulation.set_device_metrics_override(width=100, height=100, device_scale_factor=float("nan"), mobile=False)),
            ("inf mouse", cdp.input_.dispatch_mouse_event(type_="mouseMoved", x=float("inf"), y=10)),
        ]:
            try:
                r = await asyncio.wait_for(tab.send(cdp.emulation.set_device_metrics_override(width=100, height=100, device_scale_factor=float("nan"), mobile=False)) if False else tab.send(cmd), 4)
                print(label, "returned", r)
            except asyncio.TimeoutError:
                print(label, "HUNG 4s; tab.mapper pending ids:", list(tab.mapper))
            except ProtocolException as e:
                print(label, "ProtocolException", e)
        print("id-less error frames:", raw)
        print("connection still usable:", await asyncio.wait_for(tab.evaluate("2+2"), 5))

        print("\n--- A1.8 error data ---")
        try:
            await asyncio.wait_for(tab.send(cdp.page.navigate(url=None)), 5)
        except ProtocolException as e:
            print("str(e):", repr(str(e)))
            print("args[0]:", e.args[0])
    finally:
        await browser.stop()


asyncio.run(main())
