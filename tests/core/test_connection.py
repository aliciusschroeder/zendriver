import asyncio
import json
from typing import Any

import pytest
import websockets

import zendriver as zd
from zendriver.core.connection import Connection, Listener


class FakeWebSocket:
    """Replies to every command with an empty result."""

    def __init__(self) -> None:
        self.closed = False
        self._replies: asyncio.Queue[str] = asyncio.Queue()

    async def send(self, message: str) -> None:
        self._replies.put_nowait(
            json.dumps({"id": json.loads(message)["id"], "result": {}})
        )

    async def recv(self) -> str:
        return await self._replies.get()

    async def close(self) -> None:
        self.closed = True


async def test_concurrent_sends_open_a_single_websocket(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    opened: list[FakeWebSocket] = []
    listeners: list[Listener] = []

    async def slow_connect(*args: Any, **kwargs: Any) -> FakeWebSocket:
        await asyncio.sleep(0.05)
        websocket = FakeWebSocket()
        opened.append(websocket)
        return websocket

    listener_init = Listener.__init__

    def tracking_listener_init(self: Listener, connection: Connection) -> None:
        listener_init(self, connection)
        listeners.append(self)

    monkeypatch.setattr(websockets, "connect", slow_connect)
    monkeypatch.setattr(Listener, "__init__", tracking_listener_init)

    connection = Connection("ws://fake/devtools/browser/fake")
    try:
        await asyncio.wait_for(
            asyncio.gather(
                *(
                    connection.send(zd.cdp.target.set_discover_targets(discover=True))
                    for _ in range(5)
                )
            ),
            timeout=5,
        )

        assert len(opened) == 1
        assert len(listeners) == 1
    finally:
        await connection.aclose()

    assert opened[0].closed


class RecordingWebSocket(FakeWebSocket):
    """Also records the method of every command sent over it."""

    def __init__(self) -> None:
        super().__init__()
        self.methods: list[str] = []

    async def send(self, message: str) -> None:
        self.methods.append(json.loads(message)["method"])
        await super().send(message)


async def test_send_drops_stale_domain_while_enabling_a_new_one(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    websocket = RecordingWebSocket()

    async def connect(*args: Any, **kwargs: Any) -> RecordingWebSocket:
        return websocket

    monkeypatch.setattr(websockets, "connect", connect)

    def handler(event: Any) -> None:
        pass

    connection = Connection("ws://fake/devtools/page/fake")
    try:
        connection.add_handler(zd.cdp.network.RequestWillBeSent, handler)
        await asyncio.wait_for(connection.send(zd.cdp.page.bring_to_front()), 5)
        assert connection.enabled_domains == [zd.cdp.network]

        # network is now stale and page still has to be enabled: the nested
        # Page.enable send drops network before the outer pass gets to it
        connection.remove_handlers(zd.cdp.network.RequestWillBeSent, handler)
        connection.add_handler(zd.cdp.page.LoadEventFired, handler)
        websocket.methods.clear()
        await asyncio.wait_for(connection.send(zd.cdp.page.bring_to_front()), 5)

        assert websocket.methods == ["Page.enable", "Page.bringToFront"]
        assert connection.enabled_domains == [zd.cdp.page]
    finally:
        await connection.aclose()
