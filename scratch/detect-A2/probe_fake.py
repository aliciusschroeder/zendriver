import asyncio, json
import websockets
from zendriver import cdp
from zendriver.core.connection import Connection, ProtocolException

async def handler(ws):
    async for raw in ws:
        msg = json.loads(raw)
        if msg["method"] == "Runtime.evaluate":
            # a reply the generated parser can't handle (e.g. protocol drift)
            await ws.send(json.dumps({"id": msg["id"], "result": {"result": {"type": "object", "unexpectedShape": 1}, "exceptionDetails": {"bogus": 1}}}))
        elif msg["method"] == "Page.navigate":
            pass  # never answer
        else:
            await ws.send(json.dumps({"id": msg["id"], "result": {}}))

async def main():
    async with websockets.serve(handler, "127.0.0.1", 0) as server:
        port = server.sockets[0].getsockname()[1]
        conn = Connection(f"ws://127.0.0.1:{port}/devtools/browser/x")
        # C: generated command whose response fails to parse
        try:
            r = await asyncio.wait_for(conn.send(cdp.runtime.evaluate("1")), 3)
            print("C: returned", r)
        except asyncio.TimeoutError:
            print("C: send() hung; listener running:", conn.listener.running,
                  "listener exc:", repr(conn.listener.task.exception()) if conn.listener.task.done() else None)
        # shared exception instance on close
        tasks = [asyncio.create_task(conn.send(cdp.page.navigate(f"https://e{i}.example"))) for i in range(3)]
        await asyncio.sleep(0.3)
        await conn.aclose()
        for t in tasks:
            try:
                await t
            except ProtocolException as e:
                print("pending send got:", repr(e.message), "same obj:", id(e))

asyncio.run(asyncio.wait_for(main(), 20))
