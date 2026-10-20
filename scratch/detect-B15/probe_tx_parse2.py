import asyncio, json
import websockets
from zendriver import cdp
from zendriver.core.connection import Connection

async def handler(ws):
    async for raw in ws:
        msg = json.loads(raw)
        await ws.send(json.dumps({"id": msg["id"], "result": {}}))  # missing targetInfo

async def main():
    async with websockets.serve(handler, "127.0.0.1", 0) as server:
        port = server.sockets[0].getsockname()[1]
        conn = Connection(f"ws://127.0.0.1:{port}")
        t = asyncio.create_task(conn.send(cdp.target.get_target_info()))
        await asyncio.sleep(1)
        await conn.aclose()
        done, _ = await asyncio.wait({t}, timeout=3)
        print("after aclose(): send finished?", bool(done), "| tx in mapper:", len(conn.mapper))
        t.cancel()

asyncio.run(main())
