import asyncio, json
import websockets
from websockets.asyncio.server import serve

class FakePeer:
    """records every received frame; replies {} to all methods except those in self.drop;
    self.custom[method] -> dict reply (merged with id)"""
    def __init__(self):
        self.received = []
        self.drop = set()
        self.custom = {}
        self.raw = []
    async def handler(self, ws):
        async for raw in ws:
            self.raw.append(raw)
            try:
                msg = json.loads(raw)
            except Exception as e:
                # behave like chrome: id-less parse error
                await ws.send(json.dumps({"error": {"code": -32700, "message": "JSON: invalid token"}}))
                continue
            self.received.append((msg.get("method"), msg.get("params")))
            m = msg.get("method")
            if m in self.drop:
                continue
            if m in self.custom:
                rep = dict(self.custom[m]); rep["id"] = msg["id"]
            else:
                rep = {"id": msg["id"], "result": {}}
            await ws.send(json.dumps(rep))
    async def __aenter__(self):
        self.server = await serve(self.handler, "127.0.0.1", 0)
        port = self.server.sockets[0].getsockname()[1]
        self.url = f"ws://127.0.0.1:{port}"
        return self
    async def __aexit__(self, *a):
        self.server.close()
        await self.server.wait_closed()
