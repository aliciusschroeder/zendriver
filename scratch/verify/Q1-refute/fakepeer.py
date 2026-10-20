import asyncio, json
import websockets
from websockets.asyncio.server import serve

GOOD_TARGET = {"targetId": "T1", "type": "page", "title": "t", "url": "about:blank",
               "attached": True, "canAccessOpener": False}
VERSION = {"protocolVersion": "1.3", "product": "Fake/1", "revision": "r", "userAgent": "ua", "jsVersion": "js"}

class FakePeer:
    """behaviour: dict method -> callable(msg) returning list of frames (str or dict) to send"""
    def __init__(self, behaviour):
        self.behaviour = behaviour
        self.received = []
        self.server = None
    async def handler(self, ws):
        try:
            async for raw in ws:
                msg = json.loads(raw)
                self.received.append(msg)
                fn = self.behaviour.get(msg["method"])
                frames = fn(msg) if fn else [{"id": msg["id"], "result": {}}]
                for fr in frames:
                    if isinstance(fr, tuple):  # ("delay", seconds)
                        await asyncio.sleep(fr[1]); continue
                    await ws.send(fr if isinstance(fr, str) else json.dumps(fr))
        except websockets.exceptions.ConnectionClosed:
            pass
    async def __aenter__(self):
        self.server = await serve(self.handler, "127.0.0.1", 0)
        port = self.server.sockets[0].getsockname()[1]
        self.url = f"ws://127.0.0.1:{port}/devtools/browser/fake"
        return self
    async def __aexit__(self, *a):
        self.server.close()
        await self.server.wait_closed()
