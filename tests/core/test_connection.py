import asyncio
import gc
import json
import logging
import sys
import types
from typing import Any, Callable, Generator, cast

import pytest
import websockets
from pytest_mock import MockerFixture

import zendriver as zd
from zendriver.core.connection import Connection, Listener, ProtocolException

Command = dict[str, Any]


class FakeWebSocket:
    """Replies to every command with an empty result (``results[method]`` if
    given), after the frames ``before_reply(command)`` returns and before those
    ``after_reply(command)`` returns: a dict frame is sent as json, a str frame
    as is, and an exception is raised from recv()."""

    def __init__(
        self,
        results: dict[str, dict[str, Any]] | None = None,
        before_reply: Callable[[Command], list[Any]] | None = None,
        after_reply: Callable[[Command], list[Any]] | None = None,
    ) -> None:
        self.closed = False
        self._results = results or {}
        self._before_reply = before_reply
        self._after_reply = after_reply
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
        if self._after_reply is not None:
            for frame in self._after_reply(command):
                self._frames.put_nowait(frame)

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


class StalledEnableWebSocket(FakeWebSocket):
    """
    never answers Network.enable, like a page whose renderer is busy or blocked
    by an alert(). with ``hold_send`` the enable does not even leave the socket.
    the first ``rejected_enables`` are rejected instead, like chrome rejects
    CSS.enable until DOM is enabled
    """

    def __init__(self, hold_send: bool = False, rejected_enables: int = 0) -> None:
        super().__init__()
        self.hold_send = hold_send
        self.rejected_enables = rejected_enables
        self.stall_enable = True
        self.enable_stalled = asyncio.Event()
        self.delivered: list[str] = []
        self.stalled_ids: list[int] = []

    async def send(self, message: str) -> None:
        command = json.loads(message)
        method = command["method"]
        if method == "Network.enable" and self.rejected_enables:
            self.rejected_enables -= 1
            self.delivered.append(method)
            self._frames.put_nowait(
                {"id": command["id"], "error": {"code": -32000, "message": "no"}}
            )
            return
        if method == "Network.enable" and self.stall_enable:
            self.enable_stalled.set()
            if self.hold_send:
                await asyncio.Event().wait()
            self.delivered.append(method)
            self.stalled_ids.append(command["id"])
            return
        self.delivered.append(method)
        await super().send(message)


def connection_with_network_handler(
    monkeypatch: pytest.MonkeyPatch, websocket: FakeWebSocket
) -> Connection:
    async def connect(*args: Any, **kwargs: Any) -> FakeWebSocket:
        return websocket

    monkeypatch.setattr(websockets, "connect", connect)
    connection = Connection("ws://fake/devtools/browser/fake")
    # Network is not enabled yet, so the next send enables it first
    connection.add_handler(zd.cdp.network.RequestWillBeSent, lambda event: None)
    return connection


async def close_and_finish(connection: Connection, task: asyncio.Task[Any]) -> None:
    await connection.aclose()
    for _ in range(3):
        if task.done():
            break
        task.cancel()
        await asyncio.wait({task}, timeout=1)
    if task.done() and not task.cancelled():
        task.exception()


async def test_send_timeout_during_domain_enable_is_not_swallowed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    websocket = StalledEnableWebSocket()
    connection = connection_with_network_handler(monkeypatch, websocket)
    task = asyncio.create_task(
        asyncio.wait_for(
            connection.send(zd.cdp.target.set_discover_targets(discover=True)),
            timeout=0.5,
        )
    )
    try:
        # independent of the timeout under test, so a swallowed one can't hang us
        await asyncio.wait({task}, timeout=5)

        assert task.done(), "send() kept running after its timeout"
        assert isinstance(task.exception(), asyncio.TimeoutError)
        # neither the enable was sent again nor the command after the timeout
        assert websocket.delivered == ["Network.enable"]
    finally:
        await close_and_finish(connection, task)


async def test_cancelled_domain_enable_is_sent_again(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    websocket = StalledEnableWebSocket(hold_send=True)
    connection = connection_with_network_handler(monkeypatch, websocket)
    task = asyncio.create_task(
        connection.send(zd.cdp.target.set_discover_targets(discover=True))
    )
    try:
        await asyncio.wait_for(websocket.enable_stalled.wait(), timeout=5)
        task.cancel()
        await asyncio.wait({task}, timeout=5)

        assert task.cancelled(), "send() ignored the cancellation"
        assert websocket.delivered == []

        # the cancelled enable never reached the browser, so the next send
        # must enable the domain, or its events are never delivered
        websocket.stall_enable = False
        await asyncio.wait_for(
            connection.send(zd.cdp.target.set_discover_targets(discover=True)),
            timeout=5,
        )
        assert websocket.delivered == ["Network.enable", "Target.setDiscoverTargets"]
        assert zd.cdp.network in connection.enabled_domains
    finally:
        await close_and_finish(connection, task)


async def test_timed_out_domain_enable_that_was_sent_is_not_sent_again(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    websocket = StalledEnableWebSocket()
    connection = connection_with_network_handler(monkeypatch, websocket)
    try:
        with pytest.raises(asyncio.TimeoutError):
            await asyncio.wait_for(
                connection.send(zd.cdp.target.set_discover_targets(discover=True)),
                timeout=0.5,
            )
        assert websocket.delivered == ["Network.enable"]

        # the enable reached the browser and is still pending, e.g. while a
        # dialog blocks the page. enabling the domain again before every
        # command would make each one wait behind it, the one that handles
        # the dialog too
        await asyncio.wait_for(
            connection.send(zd.cdp.target.set_discover_targets(discover=True)),
            timeout=2,
        )
        assert websocket.delivered == ["Network.enable", "Target.setDiscoverTargets"]
        assert zd.cdp.network in connection.enabled_domains
    finally:
        await connection.aclose()


async def test_rejected_domain_enable_whose_send_timed_out_is_sent_again(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    websocket = StalledEnableWebSocket()
    connection = connection_with_network_handler(monkeypatch, websocket)
    try:
        with pytest.raises(asyncio.TimeoutError):
            await asyncio.wait_for(
                connection.send(zd.cdp.target.set_discover_targets(discover=True)),
                timeout=0.5,
            )

        # the browser answers the enable after its send was given up on
        (enable_id,) = websocket.stalled_ids
        websocket._frames.put_nowait(
            {"id": enable_id, "error": {"code": -32000, "message": "rejected"}}
        )
        for _ in range(100):
            if zd.cdp.network not in connection.enabled_domains:
                break
            await asyncio.sleep(0.01)
        assert zd.cdp.network not in connection.enabled_domains

        websocket.stall_enable = False
        await asyncio.wait_for(
            connection.send(zd.cdp.target.set_discover_targets(discover=True)),
            timeout=2,
        )
        assert websocket.delivered == [
            "Network.enable",
            "Network.enable",
            "Target.setDiscoverTargets",
        ]
        assert zd.cdp.network in connection.enabled_domains
    finally:
        await connection.aclose()


async def test_cancelled_send_leaves_no_command_behind(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    unhandled: list[dict[str, Any]] = []
    loop = asyncio.get_running_loop()
    loop.set_exception_handler(lambda loop, context: unhandled.append(context))
    # the enable is rejected while send() opens the connection, and stalls when
    # send() tries again for its own command, which is then already registered
    websocket = StalledEnableWebSocket(hold_send=True, rejected_enables=1)
    connection = connection_with_network_handler(monkeypatch, websocket)
    task = asyncio.create_task(
        connection.send(zd.cdp.target.set_discover_targets(discover=True))
    )
    try:
        await asyncio.wait_for(websocket.enable_stalled.wait(), timeout=5)
        task.cancel()
        await asyncio.wait({task}, timeout=5)
        assert task.cancelled(), "send() ignored the cancellation"

        # the command never left, so nothing waits for its response
        assert connection.mapper == {}
        await connection.aclose()
        del task
        gc.collect()
        assert not unhandled
    finally:
        loop.set_exception_handler(None)
        await connection.aclose()


class ClosingWebSocket(FakeWebSocket):
    """a write waits for ``fail_write`` and then fails, like one that meets the
    close of the connection"""

    def __init__(self) -> None:
        super().__init__()
        self.writing = asyncio.Event()
        self.fail_write = asyncio.Event()

    async def send(self, message: str) -> None:
        self.writing.set()
        await self.fail_write.wait()
        raise websockets.exceptions.ConnectionClosedOK(None, None)


async def test_close_during_a_failing_write_leaves_no_unretrieved_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    unhandled: list[dict[str, Any]] = []
    loop = asyncio.get_running_loop()
    loop.set_exception_handler(lambda loop, context: unhandled.append(context))
    websocket = ClosingWebSocket()
    use_websocket(monkeypatch, websocket)
    connection = Connection("ws://fake/devtools/browser/fake")
    task = asyncio.create_task(connection.send(zd.cdp.browser.close()))
    try:
        await asyncio.wait_for(websocket.writing.wait(), timeout=5)
        # like a concurrent Browser.stop(): the close fails the pending command
        # and then its write
        await connection.aclose()
        websocket.fail_write.set()
        await asyncio.wait({task}, timeout=5)
        assert isinstance(
            task.exception(), websockets.exceptions.ConnectionClosedOK
        ), "send() did not raise the error of its write"

        del task
        gc.collect()
        assert not unhandled
    finally:
        loop.set_exception_handler(None)
        await connection.aclose()


async def test_cancelled_manual_enable_is_enabled_for_handlers_later(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # the stall hits send()'s own domain enables, after Page counts as enabled
    websocket = StalledEnableWebSocket(hold_send=True, rejected_enables=1)
    connection = connection_with_network_handler(monkeypatch, websocket)
    task = asyncio.create_task(connection.send(zd.cdp.page.enable()))
    try:
        await asyncio.wait_for(websocket.enable_stalled.wait(), timeout=5)
        task.cancel()
        await asyncio.wait({task}, timeout=5)
        assert task.cancelled(), "send() ignored the cancellation"
        assert websocket.delivered == ["Network.enable"]

        # Page.enable was never sent, so a Page handler must still enable it
        assert zd.cdp.page not in connection.manually_enabled_domains
        websocket.stall_enable = False
        connection.add_handler(zd.cdp.page.LoadEventFired, lambda event: None)
        await asyncio.wait_for(
            connection.send(zd.cdp.target.set_discover_targets(discover=True)),
            timeout=5,
        )
        assert "Page.enable" in websocket.delivered
        assert zd.cdp.page in connection.enabled_domains
    finally:
        await close_and_finish(connection, task)


async def test_command_that_failed_while_enabling_domains_is_not_sent(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    sent: list[str] = []

    def receive_error_before_enable_reply(command: Command) -> list[Any]:
        sent.append(command["method"])
        if command["method"] == "Network.enable":
            return [RuntimeError("cannot receive")]
        return []

    connection = connection_with_network_handler(
        monkeypatch, FakeWebSocket(before_reply=receive_error_before_enable_reply)
    )
    try:
        # the receive error fails the command while its send() still enables
        # the domain. it must not run in the browser after the caller is told
        # that it failed
        with pytest.raises(RuntimeError):
            await asyncio.wait_for(
                connection.send(zd.cdp.target.set_discover_targets(discover=True)),
                timeout=2,
            )
        assert "Network.enable" in sent
        assert "Target.setDiscoverTargets" not in sent
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


async def test_receive_error_spares_responses_routed_to_a_session(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fail_after_next_session_reply = False

    def receive_error_after_reply(command: Command) -> list[Any]:
        nonlocal fail_after_next_session_reply
        if "sessionId" in command and fail_after_next_session_reply:
            fail_after_next_session_reply = False
            return ["not json"]
        return []

    use_websocket(
        monkeypatch,
        FakeWebSocket(
            results={
                "Target.attachToTarget": {"sessionId": "S1"},
                "Runtime.evaluate": {"result": {"type": "number", "value": 2}},
            },
            after_reply=receive_error_after_reply,
        ),
    )
    browser_connection = Connection("ws://fake/devtools/browser/fake")
    tab = flat_session_tab(browser_connection)
    try:
        await asyncio.wait_for(tab.send(zd.cdp.page.bring_to_front()), timeout=2)

        # the response is routed to the tab before the browser connection's
        # listener reads a frame it cannot parse. the command has its answer
        fail_after_next_session_reply = True
        remote_object, _ = await asyncio.wait_for(
            tab.send(zd.cdp.runtime.evaluate("1 + 1")), timeout=2
        )
        assert remote_object.value == 2
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
