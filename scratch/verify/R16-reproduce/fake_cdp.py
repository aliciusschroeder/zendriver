"""Minimal fake CDP peer for R16 reproducers (scratch only)."""

from __future__ import annotations

import asyncio
import json
from typing import Any

from websockets.asyncio.server import serve

TARGET_INFO = {
    "targetInfo": {
        "targetId": "T1",
        "type": "page",
        "title": "fake",
        "url": "about:blank",
        "attached": True,
        "canAccessOpener": False,
    }
}


class FakeCDP:
    def __init__(
        self,
        drop: set[str] | None = None,
        handshake_delay: float = 0.0,
        flood_interval: float | None = None,
    ) -> None:
        self.drop = drop or set()
        self.handshake_delay = handshake_delay
        self.flood_interval = flood_interval
        self.connections: list[Any] = []
        self.handshakes_started = 0
        self.received: list[dict[str, Any]] = []
        self.server: Any = None
        self.url = ""
        self.flooding = True

    async def _process_request(self, connection: Any, request: Any) -> None:
        self.handshakes_started += 1
        if self.handshake_delay:
            await asyncio.sleep(self.handshake_delay)
        return None

    async def _handler(self, ws: Any) -> None:
        self.connections.append(ws)
        flood_task = None
        if self.flood_interval:
            flood_task = asyncio.create_task(self._flood(ws))
        try:
            async for raw in ws:
                msg = json.loads(raw)
                self.received.append(msg)
                method = msg.get("method")
                if method in self.drop:
                    continue
                result: dict[str, Any] = {}
                if method == "Target.getTargetInfo":
                    result = TARGET_INFO
                reply = {"id": msg["id"], "result": result}
                if "sessionId" in msg:
                    reply["sessionId"] = msg["sessionId"]
                await ws.send(json.dumps(reply))
        except Exception:
            pass
        finally:
            if flood_task:
                flood_task.cancel()

    async def _flood(self, ws: Any) -> None:
        ts = 1.0
        while True:
            await asyncio.sleep(self.flood_interval)
            if not self.flooding:
                continue
            ts += 1
            try:
                await ws.send(
                    json.dumps(
                        {
                            "method": "Page.domContentEventFired",
                            "params": {"timestamp": ts},
                        }
                    )
                )
            except Exception:
                return

    async def start(self) -> "FakeCDP":
        self.server = await serve(
            self._handler,
            "127.0.0.1",
            0,
            process_request=self._process_request,
        )
        port = list(self.server.sockets)[0].getsockname()[1]
        self.url = f"ws://127.0.0.1:{port}/devtools/browser/fake"
        return self

    def open_connections(self) -> int:
        from websockets.protocol import State

        return sum(1 for c in self.connections if c.state is State.OPEN)

    async def close_all(self, code: int = 1001) -> None:
        for c in list(self.connections):
            await c.close(code=code, reason="fake peer closing")

    async def stop(self) -> None:
        self.server.close()
        await self.server.wait_closed()
