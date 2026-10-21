"""Raw CDP: gap between Target.attachToTarget reply and detachedFromTarget when the
target is closing at attach time (real headless Chromium)."""
import asyncio, json, time, sys
import websockets
import zendriver
print("zendriver from", zendriver.__file__, "py", sys.version.split()[0])

async def main():
    browser = await zendriver.start(headless=True)
    try:
        url = browser.connection.websocket_url
        async with websockets.connect(url, max_size=2**26) as ws:
            n = [5000]
            frames = []
            async def reader():
                while True:
                    raw = await ws.recv(); frames.append((time.perf_counter(), json.loads(raw)))
            rt = asyncio.create_task(reader())
            async def send(method, params, sid=None):
                n[0] += 1
                msg = {"id": n[0], "method": method, "params": params}
                if sid: msg["sessionId"] = sid
                await ws.send(json.dumps(msg)); return n[0]
            async def wait_id(i):
                for _ in range(500):
                    for ts, m in frames:
                        if m.get("id") == i: return ts, m
                    await asyncio.sleep(0.01)
            for mode in ["d0","d1","d2","d3","d4","d5","d6"]:
                for trial in range(4):
                    i = await send("Target.createTarget", {"url": "about:blank"})
                    _, m = await wait_id(i); tid = m["result"]["targetId"]
                    await asyncio.sleep(0.2)
                    start = len(frames)
                    c = await send("Target.closeTarget", {"targetId": tid})
                    d = int(mode[1:]) / 1000
                    t0 = time.perf_counter()
                    while time.perf_counter() - t0 < d: pass
                    a = await send("Target.attachToTarget", {"targetId": tid, "flatten": True})
                    await asyncio.sleep(0.6)
                    ta, ma = await wait_id(a)
                    sid = ma.get("result", {}).get("sessionId")
                    det = [ts for ts, m in frames[start:] if m.get("method") == "Target.detachedFromTarget" and m["params"].get("sessionId") == sid]
                    print(mode, "attach reply:", "sessionId" if sid else ma.get("error"),
                          "detach gap ms:", round((det[0] - ta) * 1000, 3) if det else None)
            rt.cancel()
    finally:
        await browser.stop()

asyncio.run(main())
