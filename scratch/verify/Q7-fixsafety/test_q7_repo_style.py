import asyncio
import json
from typing import Any

import pytest
import websockets

import zendriver as zd
from zendriver.core.connection import Connection

print("zendriver imported from:", zd.__file__)


class FakeWebSocket:
    """Replies to every command with an empty result."""

    def __init__(self) -> None:
        self.closed = False
        self.methods: list[str] = []
        self._replies: asyncio.Queue[str] = asyncio.Queue()

    async def send(self, message: str) -> None:
        data = json.loads(message)
        self.methods.append(data["method"])
        self._replies.put_nowait(json.dumps({"id": data["id"], "result": {}}))

    async def recv(self) -> str:
        return await self._replies.get()

    async def close(self) -> None:
        self.closed = True


async def test_send_prunes_stale_domain_while_enabling_a_new_one(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    websocket = FakeWebSocket()

    async def connect(*args: Any, **kwargs: Any) -> FakeWebSocket:
        return websocket

    monkeypatch.setattr(websockets, "connect", connect)

    def handler(event: Any) -> None:
        pass

    connection = Connection("ws://fake/devtools/page/fake")
    try:
        connection.add_handler(zd.cdp.network.RequestWillBeSent, handler)
        await asyncio.wait_for(connection.send(zd.cdp.page.bring_to_front()), 5)
        assert connection.enabled_domains == [zd.cdp.network]

        connection.remove_handlers(zd.cdp.network.RequestWillBeSent, handler)
        connection.add_handler(zd.cdp.page.LoadEventFired, handler)
        websocket.methods.clear()
        await asyncio.wait_for(connection.send(zd.cdp.page.bring_to_front()), 5)

        assert websocket.methods == ["Page.enable", "Page.bringToFront"]
        assert connection.enabled_domains == [zd.cdp.page]
    finally:
        await connection.aclose()
