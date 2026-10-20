import asyncio, json, websockets
import zendriver as zd

async def main():
    browser = await zd.start(headless=True)
    try:
        async with websockets.connect(browser.websocket_url, max_size=2**28) as ws:
            await ws.send(json.dumps({"id": 1, "method": "Runtime.evaluate", "params": {"expression": "1"}, "sessionId": "DEADBEEF"}))
            print("reply:", await asyncio.wait_for(ws.recv(), 5))
            tid = browser.main_tab.target_id
            await ws.send(json.dumps({"id": 2, "method": "Target.attachToTarget", "params": {"targetId": tid, "flatten": True}}))
            sid = None
            while sid is None:
                d = json.loads(await asyncio.wait_for(ws.recv(), 5))
                if d.get("id") == 2: sid = d["result"]["sessionId"]
            await ws.send(json.dumps({"id": 3, "method": "Target.detachFromTarget", "params": {"sessionId": sid}}))
            await ws.send(json.dumps({"id": 4, "method": "Runtime.evaluate", "params": {"expression": "1"}, "sessionId": sid}))
            for _ in range(4):
                try:
                    print("msg:", (await asyncio.wait_for(ws.recv(), 2))[:300])
                except asyncio.TimeoutError:
                    print("no more"); break
    finally:
        await browser.stop()

asyncio.run(asyncio.wait_for(main(), 50))
