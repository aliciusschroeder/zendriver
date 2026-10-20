import asyncio, json
import zendriver as zd

async def main():
    browser = await zd.start(headless=True)
    try:
        tab = await browser.get("about:blank")
        await tab.evaluate("1")
        bc = browser.connection
        ws = bc.websocket
        orig_recv = ws.recv
        log = []
        async def recv(*a, **k):
            m = await orig_recv(*a, **k)
            log.append(m[:300])
            return m
        ws.recv = recv
        await asyncio.sleep(0.5)
        log.clear()
        cmd = zd.cdp.emulation.set_device_metrics_override(width=100, height=100, device_scale_factor=float("nan"), mobile=False)
        try:
            r = await asyncio.wait_for(tab.send(cmd), 4)
            print("result", r)
        except asyncio.TimeoutError:
            print("send HUNG 4s; pending tab.mapper:", list(tab.mapper))
        except Exception as e:
            print("raised", type(e).__name__, e)
        for m in log:
            print("recv:", m)
        print("websocket state:", ws.state)
        print("still usable:", await asyncio.wait_for(tab.evaluate("2+2"), 5))
    finally:
        await browser.stop()

asyncio.run(main())
