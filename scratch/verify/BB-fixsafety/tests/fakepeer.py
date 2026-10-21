"""A tiny in-process fake CDP peer for browser-free tests."""

import asyncio
import json
from typing import Any, Callable, Optional

import websockets.asyncio.server


class FakePeer:
    def __init__(self) -> None:
        self.received: list[dict[str, Any]] = []
        # method -> None (drop) or callable(msg) -> reply dict
        self.behaviour: dict[str, Optional[Callable[[dict[str, Any]], dict[str, Any]]]] = {}
        self.server: Any = None
        self.ws: Any = None
        self.raw: list[str] = []

    @property
    def methods(self) -> list[str]:
        return [m.get("method", "<invalid>") for m in self.received]

    async def _handler(self, ws: Any) -> None:
        self.ws = ws
        async for raw in ws:
            self.raw.append(raw)
            try:
                msg = json.loads(raw)
            except ValueError:
                # emulate chrome: unparsable frame -> id-less error
                self.received.append({"method": "<invalid>", "raw": raw})
                await ws.send(
                    json.dumps(
                        {"error": {"code": -32700, "message": "JSON: invalid token"}}
                    )
                )
                continue
            self.received.append(msg)
            method = msg.get("method")
            if method in self.behaviour:
                b = self.behaviour[method]
                if b is None:
                    continue  # drop
                await ws.send(json.dumps(b(msg)))
                continue
            await ws.send(json.dumps({"id": msg["id"], "result": {}}))

    async def start(self) -> str:
        self.server = await websockets.asyncio.server.serve(
            self._handler, "127.0.0.1", 0
        )
        port = self.server.sockets[0].getsockname()[1]
        return f"ws://127.0.0.1:{port}"

    async def send_event(self, method: str, params: dict[str, Any]) -> None:
        await self.ws.send(json.dumps({"method": method, "params": params}))

    async def stop(self) -> None:
        self.server.close()
        await self.server.wait_closed()
