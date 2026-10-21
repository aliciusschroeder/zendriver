"""Raw CDP probe against real headless Chromium (second client on browser ws)."""
import asyncio, json, time, sys
import websockets
import zendriver
print("zendriver from", zendriver.__file__, "py", sys.version.split()[0])

class Raw:
    def __init__(self, ws):
        self.ws = ws; self.n = 1000; self.frames = []; self.waiters = {}
        self.task = asyncio.create_task(self.loop())
    async def loop(self):
        try:
            while True:
                raw = await self.ws.recv()
                t = time.perf_counter()
                m = json.loads(raw)
                self.frames.append((t, m))
                if "id" in m and m["id"] in self.waiters:
                    self.waiters.pop(m["id"]).set_result(m)
        except Exception as e:
            pass
    async def send(self, method, params=None, sid=None, wait=True):
        self.n += 1; i = self.n
        msg = {"id": i, "method": method, "params": params or {}}
        if sid: msg["sessionId"] = sid
        fut = asyncio.get_running_loop().create_future(); self.waiters[i] = fut
        await self.ws.send(json.dumps(msg))
        if wait:
            return await asyncio.wait_for(fut, 5)
        return i

async def main():
    browser = await zendriver.start(headless=True)
    try:
        url = browser.connection.websocket_url
        async with websockets.connect(url, max_size=2**26) as ws:
            r = Raw(ws)
            # (a) bogus session id
            m = await r.send("Runtime.evaluate", {"expression": "1"}, sid="DEADBEEF" * 4)
            print("(a) bogus session reply:", m)
            # (b) attach, detach, then send on old session
            t = await r.send("Target.createTarget", {"url": "about:blank"})
            tid = t["result"]["targetId"]
            a = await r.send("Target.attachToTarget", {"targetId": tid, "flatten": True})
            sid = a["result"]["sessionId"]
            await asyncio.sleep(0.2)
            print("(d) attachedToTarget events for our attach:",
                  [f[1]["params"]["sessionId"] for f in r.frames if f[1].get("method") == "Target.attachedToTarget"], "sid", sid)
            await r.send("Target.detachFromTarget", {"sessionId": sid})
            await asyncio.sleep(0.2)
            m = await r.send("Runtime.evaluate", {"expression": "1"}, sid=sid)
            print("(b) reply on detached session:", m)
            # (c) attach + Page.close via session, record order and gaps
            for trial in range(5):
                t = await r.send("Target.createTarget", {"url": "about:blank"})
                tid = t["result"]["targetId"]
                a = await r.send("Target.attachToTarget", {"targetId": tid, "flatten": True})
                sid = a["result"]["sessionId"]
                await asyncio.sleep(0.2)
                start = len(r.frames)
                i = await r.send("Page.close", {}, sid=sid, wait=False)
                await asyncio.sleep(1.0)
                seq = []
                t0 = None
                for (ts, m) in r.frames[start:]:
                    if m.get("id") == i or (m.get("method") == "Target.detachedFromTarget" and m["params"].get("sessionId") == sid):
                        t0 = t0 or ts
                        seq.append(("reply" if m.get("id") == i else "detach", round((ts - t0) * 1000, 3)))
                print("(c) Page.close via session, frame order (ms):", seq)
    finally:
        await browser.stop()

asyncio.run(main())
