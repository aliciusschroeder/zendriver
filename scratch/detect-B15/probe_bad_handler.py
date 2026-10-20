import asyncio, json, logging
import websockets
from zendriver import cdp
from zendriver.core.connection import Connection
logging.basicConfig(level=logging.CRITICAL)

EVENT = {"method": "Target.targetCreated", "params": {"targetInfo": {
    "targetId": "T1", "type": "page", "title": "", "url": "about:blank",
    "attached": False, "canAccessOpener": False}}}

async def handler(ws):
    async for raw in ws:
        msg = json.loads(raw)
        if msg["method"] == "Browser.getVersion":
            # an event arrives before the reply, as is normal in CDP
            await ws.send(json.dumps(EVENT))
            await ws.send(json.dumps({"id": msg["id"], "result": {
                "protocolVersion": "1.3", "product": "x", "revision": "r",
                "userAgent": "ua", "jsVersion": "js"}}))

async def main():
    async with websockets.serve(handler, "127.0.0.1", 0) as server:
        port = server.sockets[0].getsockname()[1]
        conn = Connection(f"ws://127.0.0.1:{port}")
        good_calls = []
        conn.add_handler(cdp.target.TargetCreated, lambda e: good_calls.append(e))
        async def bad_handler():   # wrong arity: user bug in ONE handler
            pass
        conn.add_handler(cdp.target.TargetCreated, bad_handler)
        t = asyncio.create_task(conn.send(cdp.browser.get_version()))
        done, _ = await asyncio.wait({t}, timeout=3)
        print("get_version finished within 3s:", bool(done))
        print("listener running:", conn.listener.running, "exc:",
              repr(conn.listener.task.exception()) if conn.listener.task.done() else None)
        if not done:
            t.cancel()
        await conn.aclose()

asyncio.run(main())
