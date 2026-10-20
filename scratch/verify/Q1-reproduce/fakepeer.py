"""Minimal in-process fake CDP peer for reproducers (verifier Q1-reproduce)."""

import asyncio
import json

from websockets.asyncio.server import serve

TARGET_INFO = {
    "targetId": "T1",
    "type": "page",
    "title": "t",
    "url": "about:blank",
    "attached": True,
    "canAccessOpener": False,
}


class FakePeer:
    """overrides: dict method -> async fn(peer, ws, msg) that does the replying itself.
    default reply is {"id":..., "result": {}} (+sessionId when present)."""

    def __init__(self, overrides=None):
        self.overrides = overrides or {}
        self.received = []
        self.server = None
        self.ws = None

    async def start(self):
        self.server = await serve(self._handler, "127.0.0.1", 0)
        port = list(self.server.sockets)[0].getsockname()[1]
        self.url = f"ws://127.0.0.1:{port}/devtools/browser/fake"
        return self

    async def stop(self):
        self.server.close()
        await self.server.wait_closed()

    @staticmethod
    def reply(msg, result=None, **extra):
        out = {"id": msg["id"]}
        if result is not None:
            out["result"] = result
        if "sessionId" in msg:
            out["sessionId"] = msg["sessionId"]
        out.update(extra)
        return json.dumps(out)

    async def default(self, ws, msg):
        m = msg["method"]
        if m == "Target.getTargetInfo":
            await ws.send(self.reply(msg, {"targetInfo": TARGET_INFO}))
        elif m == "Browser.getVersion":
            await ws.send(
                self.reply(
                    msg,
                    {
                        "protocolVersion": "1.3",
                        "product": "Fake/1",
                        "revision": "r",
                        "userAgent": "UA",
                        "jsVersion": "1",
                    },
                )
            )
        elif m == "Target.attachToTarget":
            await ws.send(self.reply(msg, {"sessionId": "S1"}))
        elif m == "Runtime.evaluate":
            await ws.send(
                self.reply(msg, {"result": {"type": "number", "value": 4, "description": "4"}})
            )
        else:
            await ws.send(self.reply(msg, {}))

    async def _handler(self, ws):
        self.ws = ws
        async for raw in ws:
            msg = json.loads(raw)
            self.received.append(msg)
            fn = self.overrides.get(msg["method"])
            if fn is not None:
                asyncio.create_task(fn(self, ws, msg))
            else:
                await self.default(ws, msg)
