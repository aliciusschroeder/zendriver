import asyncio, json
import websockets
from zendriver import cdp
from zendriver.core.connection import Connection

async def handler(ws):
    async for raw in ws:
        pass  # never answers

async def main():
    async with websockets.serve(handler, "127.0.0.1", 0) as server:
        port = server.sockets[0].getsockname()[1]
        conn = Connection(f"ws://127.0.0.1:{port}")
        tasks = [asyncio.create_task(conn.send(c)) for c in
                 (cdp.browser.get_version(), cdp.page.reload(), cdp.dom.get_document())]
        await asyncio.sleep(0.3)
        await conn.aclose()
        res = await asyncio.gather(*tasks, return_exceptions=True)
        for r in res:
            print(repr(str(r)))
        print("same instance:", res[0] is res[1] is res[2])

asyncio.run(main())
