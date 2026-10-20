import asyncio, json, sys, time
from websockets.asyncio.server import serve
import zendriver
from zendriver import cdp
from zendriver.core.connection import Connection
print("zendriver from", zendriver.__file__, "python", sys.version.split()[0])
SEEN = []
async def answer(ws, msg, delay):
    await asyncio.sleep(delay)
    res = {"result": {"type": "number", "value": 2}} if msg["method"] == "Runtime.evaluate" else {}
    await ws.send(json.dumps({"id": msg["id"], "result": res}))
async def handler(ws):
    async for raw in ws:
        msg = json.loads(raw)
        SEEN.append((round(time.monotonic() - T0, 2), msg["method"]))
        asyncio.create_task(answer(ws, msg, 2.0 if msg["method"] == "Network.enable" else 0))
async def main():
    global T0
    async with serve(handler, "127.0.0.1", 0) as server:
        url = f"ws://127.0.0.1:{server.sockets[0].getsockname()[1]}"
        conn = Connection(url)
        await conn.aopen()
        conn.add_handler(cdp.network.RequestWillBeSent, lambda e: None)
        T0 = time.monotonic()
        try:
            r = await asyncio.wait_for(asyncio.wait_for(conn.send(cdp.runtime.evaluate("1+1")), 1.0), 20)
            print(f"wait_for(timeout=1) returned {r!r} after {time.monotonic()-T0:.2f}s (no TimeoutError)")
        except BaseException as e:
            print(f"raised {type(e).__name__} after {time.monotonic()-T0:.2f}s")
        print("sent:", SEEN)
        await conn.aclose()
asyncio.run(main())
