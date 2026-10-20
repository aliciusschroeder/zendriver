"""Minimal fake CDP peer for probing zendriver Connection behaviour."""
import asyncio
import json
from typing import Any, Callable

import websockets


class FakeCDP:
    def __init__(self, behaviour: Callable[[dict[str, Any]], Any]):
        # behaviour(msg) -> dict result | "noreply" | "close" | ("error", {...}) | ("raw", dict)
        self.behaviour = behaviour
        self.received: list[dict[str, Any]] = []
        self.server = None
        self.clients: list[Any] = []

    async def handler(self, ws: Any) -> None:
        self.clients.append(ws)
        try:
            async for raw in ws:
                msg = json.loads(raw)
                self.received.append(msg)
                b = self.behaviour(msg)
                if asyncio.iscoroutine(b):
                    b = await b
                if b == "noreply":
                    continue
                if b == "close":
                    await ws.close()
                    return
                if isinstance(b, tuple) and b[0] == "error":
                    reply = {"id": msg["id"], "error": b[1]}
                elif isinstance(b, tuple) and b[0] == "raw":
                    reply = b[1]
                else:
                    reply = {"id": msg["id"], "result": b}
                if "sessionId" in msg:
                    reply["sessionId"] = msg["sessionId"]
                await ws.send(json.dumps(reply))
        except websockets.exceptions.ConnectionClosed:
            pass

    async def start(self) -> str:
        self.server = await websockets.serve(self.handler, "127.0.0.1", 0)
        port = self.server.sockets[0].getsockname()[1]
        return f"ws://127.0.0.1:{port}/devtools/browser/fake"

    async def stop(self) -> None:
        self.server.close()
        await self.server.wait_closed()
