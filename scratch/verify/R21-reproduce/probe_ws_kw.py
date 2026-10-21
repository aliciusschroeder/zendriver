import asyncio, websockets
from websockets.asyncio.server import serve
async def h(ws): await ws.wait_closed()
async def main():
    async with serve(h, "127.0.0.1", 0) as srv:
        port = srv.sockets[0].getsockname()[1]
        try:
            ws = await asyncio.wait_for(websockets.connect(f"ws://127.0.0.1:{port}", proxy=None), 5)
            print(websockets.__version__, "proxy=None accepted"); await ws.close()
        except Exception as e:
            print(websockets.__version__, "proxy=None ->", type(e).__name__, e)
asyncio.run(main())
