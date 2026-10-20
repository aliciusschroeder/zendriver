import asyncio, json
import zendriver as zd

async def main():
    browser = await zd.start(headless=True)
    try:
        tab = await browser.get("about:blank")
        await tab.evaluate("1")
        orig = tab.listener.connection._receive_message
        seen = []
        async def spy():
            m = await orig()
            if m is not None and ("error" in m and "id" not in m):
                seen.append(m)
            return m
        # browser-level messages: spy on the browser connection instead (session replies are routed)
        bc = browser.connection
        borig = bc._receive_message
        async def bspy():
            m = await borig()
            if m is not None and "method" not in m:
                seen.append(("browser", m))
            return m
        bc._receive_message = bspy
        tab._receive_message = spy
        try:
            r = await asyncio.wait_for(tab.send(zd.cdp.emulation.set_device_metrics_override(width=100, height=100, device_scale_factor=float("nan"), mobile=False)), 5)
            print("result", r)
        except asyncio.TimeoutError:
            print("send HUNG 5s")
        except Exception as e:
            print("raised", type(e).__name__, e)
        print("unmatched msgs:", seen)
    finally:
        await browser.stop()

asyncio.run(main())
