"""
regression tests for flat session attach/detach ordering (group R22).

a fake chrome peer answers the browser websocket. like chrome, it answers a
command on an unknown session with an error that has no sessionId.
"""

import asyncio
import json
from types import SimpleNamespace
from typing import Any

import pytest
import websockets
from websockets.asyncio.server import ServerConnection, serve

import zendriver
from zendriver import cdp
from zendriver.core.connection import Connection, ProtocolException

print("zendriver imported from", zendriver.__file__)


class FakeChrome:
    def __init__(self) -> None:
        self.attach_delay = 0.0
        # send Target.detachedFromTarget in the same write as the attach reply
        self.detach_with_attach_reply = False
        # send Target.detachedFromTarget in the same write as the evaluate reply
        self.detach_with_evaluate_reply = False
        self.live: set[str] = set()
        self.attached: list[str] = []
        self.detached: list[str] = []
        self._count = 0

    @staticmethod
    def burst(ws: ServerConnection, *messages: dict[str, Any]) -> None:
        # both frames go out in one transport write, so the client reads them together
        for message in messages:
            ws.protocol.send_text(json.dumps(message).encode())
        ws.send_data()

    def detached_event(self, session_id: str) -> dict[str, Any]:
        self.live.discard(session_id)
        return {
            "method": "Target.detachedFromTarget",
            "params": {"sessionId": session_id, "targetId": "T1"},
        }

    async def attach(self, ws: ServerConnection, message: dict[str, Any]) -> None:
        self._count += 1
        session_id = f"S{self._count}"
        self.live.add(session_id)
        self.attached.append(session_id)
        if self.attach_delay:
            await asyncio.sleep(self.attach_delay)
        reply = {"id": message["id"], "result": {"sessionId": session_id}}
        if self.detach_with_attach_reply:
            self.burst(ws, reply, self.detached_event(session_id))
        else:
            self.burst(ws, reply)

    async def handler(self, ws: ServerConnection) -> None:
        try:
            async for raw in ws:
                message = json.loads(raw)
                method = message["method"]
                session_id = message.get("sessionId")
                if session_id is not None and session_id not in self.live:
                    # what chrome does: no sessionId on the error
                    self.burst(
                        ws,
                        {
                            "id": message["id"],
                            "error": {
                                "code": -32001,
                                "message": "Session with given id not found.",
                            },
                        },
                    )
                elif method == "Target.attachToTarget":
                    asyncio.create_task(self.attach(ws, message))
                elif method == "Target.detachFromTarget":
                    detached = message["params"]["sessionId"]
                    self.detached.append(detached)
                    self.burst(
                        ws,
                        {"id": message["id"], "result": {}},
                        self.detached_event(detached),
                    )
                elif method == "Runtime.evaluate":
                    reply = {
                        "id": message["id"],
                        "sessionId": session_id,
                        "result": {
                            "result": {"type": "number", "value": 2, "description": "2"}
                        },
                    }
                    if self.detach_with_evaluate_reply and session_id is not None:
                        self.burst(ws, reply, self.detached_event(session_id))
                    else:
                        self.burst(ws, reply)
                else:
                    reply = {"id": message["id"], "result": {}}
                    if session_id is not None:
                        reply["sessionId"] = session_id
                    self.burst(ws, reply)
        except websockets.exceptions.ConnectionClosed:
            pass


@pytest.fixture
async def peer() -> Any:
    fake = FakeChrome()
    async with serve(fake.handler, "127.0.0.1", 0) as server:
        port = server.sockets[0].getsockname()[1]
        browser_connection = Connection(f"ws://127.0.0.1:{port}/devtools/browser/b")
        owner = SimpleNamespace(connection=browser_connection, config=None)
        target = cdp.target.TargetInfo(
            target_id=cdp.target.TargetID("T1"),
            type_="page",
            title="",
            url="about:blank",
            attached=False,
            can_access_opener=False,
        )
        tab = Connection(
            f"ws://127.0.0.1:{port}/devtools/page/T1", target=target, _owner=owner
        )  # type: ignore[arg-type]
        try:
            yield fake, browser_connection, tab
        finally:
            await asyncio.wait_for(tab.aclose(), 5)
            await asyncio.wait_for(browser_connection.aclose(), 5)


def evaluate() -> Any:
    return cdp.runtime.evaluate("1+1")


async def test_reply_in_same_burst_as_detach_is_delivered(peer: Any) -> None:
    """A1.5: the command succeeded in chrome, so the caller must get its result"""
    fake, _, tab = peer
    await asyncio.wait_for(tab.aopen(), 5)
    fake.detach_with_evaluate_reply = True
    result = await asyncio.wait_for(tab.send(evaluate()), 5)
    assert result[0].value == 2


async def test_detach_in_same_burst_as_attach_reply_does_not_hang(peer: Any) -> None:
    """B14.7: the detach must be applied to the new session, so sends fail instead of hanging"""
    fake, browser_connection, tab = peer
    fake.detach_with_attach_reply = True
    for _ in range(2):
        with pytest.raises(ProtocolException):
            await asyncio.wait_for(tab.send(evaluate()), 3)
    assert browser_connection._sessions == {}
    assert tab.session_id is None


async def test_cancelled_first_command_does_not_orphan_a_session(peer: Any) -> None:
    """A1.6: every session chrome created for the tab is detached again"""
    fake, _, tab = peer
    fake.attach_delay = 0.3
    with pytest.raises(asyncio.TimeoutError):
        await asyncio.wait_for(tab.send(evaluate()), 0.1)
    await asyncio.sleep(0.5)  # the late attach reply arrives
    fake.attach_delay = 0
    result = await asyncio.wait_for(tab.send(evaluate()), 5)
    assert result[0].value == 2
    await asyncio.wait_for(tab.aclose(), 5)
    await asyncio.sleep(0.1)
    assert fake.attached and sorted(fake.attached) == sorted(fake.detached)


async def test_aclose_while_attach_pending_does_not_orphan_a_session(peer: Any) -> None:
    """A1.6 variant: the tab is closed before chrome answers the cancelled attach"""
    fake, browser_connection, tab = peer
    fake.attach_delay = 0.3
    with pytest.raises(asyncio.TimeoutError):
        await asyncio.wait_for(tab.send(evaluate()), 0.1)
    await asyncio.wait_for(tab.aclose(), 5)
    await asyncio.sleep(0.5)  # a late attach reply would arrive by now
    assert tab.closed and browser_connection._sessions == {}
    assert fake.attached and sorted(fake.attached) == sorted(fake.detached)
