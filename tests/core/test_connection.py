import asyncio
import json
import logging
import types
from typing import Any, Callable, Generator, cast

import pytest
import websockets

import zendriver as zd
from zendriver.core.connection import Connection, Listener, ProtocolException

Command = dict[str, Any]


class FakeWebSocket:
    """Replies to every command with an empty result (``results[method]`` if
    given), after the frames ``before_reply(command)`` returns: a dict frame is
    sent as json, a str frame as is, and an exception is raised from recv()."""

    def __init__(
        self,
        results: dict[str, dict[str, Any]] | None = None,
        before_reply: Callable[[Command], list[Any]] | None = None,
    ) -> None:
        self.closed = False
        self._results = results or {}
        self._before_reply = before_reply
        self._frames: asyncio.Queue[Any] = asyncio.Queue()

    async def send(self, message: str) -> None:
        command: Command = json.loads(message)
        if self._before_reply is not None:
            for frame in self._before_reply(command):
                self._frames.put_nowait(frame)
        reply = {
            "id": command["id"],
            "result": self._results.get(command["method"], {}),
        }
        if "sessionId" in command:
            reply["sessionId"] = command["sessionId"]
        self._frames.put_nowait(reply)

    async def recv(self) -> str:
        frame = await self._frames.get()
        if isinstance(frame, BaseException):
            raise frame
        return frame if isinstance(frame, str) else json.dumps(frame)

    async def close(self) -> None:
        self.closed = True


def use_websocket(monkeypatch: pytest.MonkeyPatch, websocket: FakeWebSocket) -> None:
    async def connect(*args: Any, **kwargs: Any) -> FakeWebSocket:
        return websocket

    monkeypatch.setattr(websockets, "connect", connect)


def flat_session_tab(browser_connection: Connection) -> Connection:
    """A page target connection that talks through a flat session of
    ``browser_connection``."""
    browser = cast(
        zd.Browser, types.SimpleNamespace(connection=browser_connection, config=None)
    )
    return Connection(
        "ws://fake/devtools/page/T1",
        target=zd.cdp.target.TargetInfo(
            target_id=zd.cdp.target.TargetID("T1"),
            type_="page",
            title="",
            url="about:blank",
            attached=False,
            can_access_opener=False,
        ),
        _owner=browser,
    )


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


def _custom_command_that_raises() -> Generator[Command, Command, Any]:
    response = yield {"method": "Runtime.evaluate", "params": {"expression": "1"}}
    return response["notThere"]


def _custom_command_that_does_not_stop() -> Generator[Command, Command, Any]:
    yield {"method": "Runtime.evaluate", "params": {"expression": "1"}}
    yield {"method": "Runtime.evaluate", "params": {"expression": "2"}}


@pytest.mark.parametrize(
    "command, cause",
    [
        # the empty result of FakeWebSocket misses the key the parser requires
        (zd.cdp.target.get_target_info, "KeyError('targetInfo')"),
        (_custom_command_that_raises, "KeyError('notThere')"),
        (_custom_command_that_does_not_stop, "None"),
    ],
    ids=["generated-parser", "custom-raises", "custom-does-not-stop"],
)
async def test_unparsable_response_fails_only_its_command(
    monkeypatch: pytest.MonkeyPatch,
    command: Callable[[], Generator[Command, Command, Any]],
    cause: str,
) -> None:
    use_websocket(monkeypatch, FakeWebSocket())
    connection = Connection("ws://fake/devtools/browser/fake")
    try:
        await connection.aopen()
        listener = connection.listener
        assert listener is not None

        with pytest.raises(ProtocolException, match="could not parse") as exc_info:
            await asyncio.wait_for(connection.send(command()), timeout=2)
        assert repr(exc_info.value.__cause__) == cause

        assert connection.listener is listener and listener.running
        await asyncio.wait_for(
            connection.send(zd.cdp.target.set_discover_targets(discover=True)),
            timeout=2,
        )
    finally:
        await connection.aclose()


async def test_handler_that_fails_when_called_does_not_stop_the_listener(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    target_info = {
        "targetId": "T1",
        "type": "page",
        "title": "",
        "url": "about:blank",
        "attached": False,
        "canAccessOpener": False,
    }

    def target_created_first(command: Command) -> list[Any]:
        return [
            {"method": "Target.targetCreated", "params": {"targetInfo": target_info}}
        ]

    use_websocket(monkeypatch, FakeWebSocket(before_reply=target_created_first))
    handled = asyncio.Event()

    async def takes_no_event() -> None:
        pass

    async def takes_the_event(event: zd.cdp.target.TargetCreated) -> None:
        handled.set()

    connection = Connection("ws://fake/devtools/browser/fake")
    connection.add_handler(zd.cdp.target.TargetCreated, takes_no_event)
    connection.add_handler(zd.cdp.target.TargetCreated, takes_the_event)
    try:
        await asyncio.wait_for(
            connection.send(zd.cdp.target.set_discover_targets(discover=True)),
            timeout=2,
        )
        await asyncio.wait_for(handled.wait(), timeout=2)
        assert connection.listener is not None and connection.listener.running
    finally:
        await connection.aclose()


@pytest.mark.parametrize(
    "bad_frame, error",
    [
        ("not json", json.JSONDecodeError),
        (RuntimeError("cannot receive"), RuntimeError),
    ],
    ids=["not-json", "recv-raises"],
)
async def test_unexpected_receive_error_fails_pending_commands(
    monkeypatch: pytest.MonkeyPatch, bad_frame: Any, error: type[Exception]
) -> None:
    sent: list[Command] = []

    def bad_frame_once(command: Command) -> list[Any]:
        sent.append(command)
        return [bad_frame] if len(sent) == 1 else []

    use_websocket(monkeypatch, FakeWebSocket(before_reply=bad_frame_once))
    connection = Connection("ws://fake/devtools/browser/fake")
    try:
        with pytest.raises(error):
            await asyncio.wait_for(
                connection.send(zd.cdp.target.set_discover_targets(discover=True)),
                timeout=2,
            )

        # the listener stops instead of retrying an error that may persist,
        # and the next command starts a new one
        listener = connection.listener
        assert listener is not None and listener.task is not None
        await asyncio.wait({listener.task}, timeout=1)
        assert not listener.running
        await asyncio.wait_for(
            connection.send(zd.cdp.target.set_discover_targets(discover=True)),
            timeout=2,
        )
        assert connection.listener is not None
        assert connection.listener is not listener and connection.listener.running
    finally:
        await connection.aclose()


async def test_flat_session_send_restarts_the_browser_listener(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fail_next_session_command = False

    def receive_error(command: Command) -> list[Any]:
        nonlocal fail_next_session_command
        if "sessionId" in command and fail_next_session_command:
            fail_next_session_command = False
            return [RuntimeError("cannot receive")]
        return []

    use_websocket(
        monkeypatch,
        FakeWebSocket(
            results={"Target.attachToTarget": {"sessionId": "S1"}},
            before_reply=receive_error,
        ),
    )
    browser_connection = Connection("ws://fake/devtools/browser/fake")
    tab = flat_session_tab(browser_connection)
    try:
        await asyncio.wait_for(tab.send(zd.cdp.page.bring_to_front()), timeout=2)
        assert tab.session_id == "S1"

        # the browser connection's listener, which reads the websocket for the
        # tab, stops while a tab command waits for its response
        fail_next_session_command = True
        with pytest.raises(RuntimeError):
            await asyncio.wait_for(tab.send(zd.cdp.page.bring_to_front()), timeout=2)

        await asyncio.wait_for(tab.send(zd.cdp.page.bring_to_front()), timeout=2)
        assert browser_connection.listener is not None
        assert browser_connection.listener.running
    finally:
        await tab.aclose()
        await browser_connection.aclose()


async def test_detaching_a_session_stops_its_listener_quietly(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    use_websocket(
        monkeypatch,
        FakeWebSocket(results={"Target.attachToTarget": {"sessionId": "S1"}}),
    )
    browser_connection = Connection("ws://fake/devtools/browser/fake")
    tab = flat_session_tab(browser_connection)

    async def send_then_close() -> None:
        # close right after a response, like browser.stop() after the last
        # command, before the tab listener started its next receive
        await tab.send(zd.cdp.page.bring_to_front())
        await tab.aclose()

    try:
        await asyncio.wait_for(send_then_close(), timeout=2)
        listener = tab.listener
        assert listener is not None and listener.task is not None
        await asyncio.wait({listener.task}, timeout=1)
        assert listener.task.done() and listener.task.exception() is None
        assert not [
            record
            for record in caplog.records
            if record.name == "uc.connection" and record.levelno >= logging.WARNING
        ]
    finally:
        await browser_connection.aclose()
