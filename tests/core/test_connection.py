import asyncio
import json
import sys
from typing import Any, Callable

import pytest
import websockets
from pytest_mock import MockerFixture

import zendriver as zd
from zendriver.core.connection import Connection, Listener, ProtocolException


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


def _exception_group() -> BaseException:
    if sys.version_info >= (3, 11):
        return ExceptionGroup("group", [ValueError("inner")])  # noqa: F821
    pytest.skip("ExceptionGroup needs Python 3.11+")


@pytest.mark.parametrize(
    "make_exception",
    [
        pytest.param(
            lambda: json.JSONDecodeError("Expecting value", "{bad", 1), id="json"
        ),
        pytest.param(
            lambda: websockets.exceptions.ConnectionClosedError(None, None),
            id="connection-closed",
        ),
        pytest.param(
            lambda: ProtocolException({"code": -32000, "message": "No node found"}),
            id="protocol",
        ),
        pytest.param(lambda: SystemExit(3), id="system-exit"),
        pytest.param(_exception_group, id="exception-group"),
    ],
)
async def test_aexit_propagates_the_original_exception(
    mocker: MockerFixture, make_exception: Callable[[], BaseException]
) -> None:
    connection = Connection("ws://fake/devtools/browser/fake")
    aclose = mocker.spy(connection, "aclose")

    exception = make_exception()
    with pytest.raises(type(exception)) as exc_info:
        async with connection:
            raise exception

    assert exc_info.value is exception
    aclose.assert_awaited_once_with()
