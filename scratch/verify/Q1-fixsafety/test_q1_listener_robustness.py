"""Q1 regression tests: the Listener must not die / leave Transactions unresolved.

Browser-free: a scriptable fake websocket stands in for websockets.connect.
Every test bounds the awaited call with asyncio.wait for a POSITIVE timeout and,
when it is still pending, prints the stuck task's stack before failing.
"""

import asyncio
import json
import types
from typing import Any, Callable

import pytest
import websockets

import zendriver as zd
from zendriver import cdp
from zendriver.core.connection import Connection, ProtocolException

print("zendriver imported from:", zd.__file__)

Responder = Callable[[dict[str, Any]], list[Any]]

TARGET_INFO = {
    "targetId": "T1",
    "type": "page",
    "title": "t",
    "url": "about:blank",
    "attached": True,
    "canAccessOpener": False,
}
VERSION = {
    "protocolVersion": "1.3",
    "product": "Chrome/1",
    "revision": "r",
    "userAgent": "ua",
    "jsVersion": "1",
}


class ScriptedWebSocket:
    """Fake websocket. `responder(command)` returns the frames to queue for recv().

    A frame that is a dict is json-encoded, a str is sent as-is, and an
    exception instance is raised from recv().
    """

    def __init__(self, responder: Responder) -> None:
        self.responder = responder
        self.closed = False
        self.sent: list[dict[str, Any]] = []
        self._frames: asyncio.Queue[Any] = asyncio.Queue()

    async def send(self, message: str) -> None:
        command = json.loads(message)
        self.sent.append(command)
        for frame in self.responder(command):
            self._frames.put_nowait(frame)

    async def recv(self) -> str:
        frame = await self._frames.get()
        if isinstance(frame, BaseException):
            raise frame
        if isinstance(frame, str):
            return frame
        return json.dumps(frame)

    async def close(self) -> None:
        self.closed = True


def reply(command: dict[str, Any], result: dict[str, Any]) -> dict[str, Any]:
    message: dict[str, Any] = {"id": command["id"], "result": result}
    if "sessionId" in command:
        message["sessionId"] = command["sessionId"]
    return message


def default_result(method: str) -> dict[str, Any]:
    if method == "Browser.getVersion":
        return dict(VERSION)
    if method == "Target.getTargetInfo":
        return {"targetInfo": dict(TARGET_INFO)}
    if method == "Target.attachToTarget":
        return {"sessionId": "S1"}
    if method == "Runtime.evaluate":
        return {"result": {"type": "number", "value": 2}}
    return {}


@pytest.fixture
def fake_ws(monkeypatch: pytest.MonkeyPatch) -> Callable[[Responder], None]:
    holder: dict[str, Responder] = {}

    async def connect(*args: Any, **kwargs: Any) -> ScriptedWebSocket:
        return ScriptedWebSocket(holder["responder"])

    monkeypatch.setattr(websockets, "connect", connect)

    def install(responder: Responder) -> None:
        holder["responder"] = responder

    return install


async def finish_within(coro: Any, timeout: float = 3.0) -> Any:
    """Await coro; if it is still pending after `timeout`, print where it is
    stuck, cancel it and fail the test."""
    task = asyncio.ensure_future(coro)
    done, _ = await asyncio.wait({task}, timeout=timeout)
    if not done:
        print("---- stuck task stack ----")
        task.print_stack()
        task.cancel()
        try:
            await asyncio.wait_for(task, 1)
        except BaseException:
            pass
        pytest.fail(f"call did not finish within {timeout}s (hang)")
    return task.result()


def listener_state(conn: Connection) -> str:
    listener = conn.listener
    if listener is None or listener.task is None:
        return "no listener"
    if not listener.task.done():
        return "running"
    if listener.task.cancelled() or listener.task.exception() is None:
        return "stopped"
    return f"dead: {listener.task.exception()!r}"


# --- A1.1 / A2.3 / B15.1: reply the parser rejects ---------------------------


@pytest.mark.parametrize(
    "bad_result,cmd_factory",
    [
        # missing required key -> KeyError in TargetInfo.from_json
        ({}, lambda: cdp.target.get_target_info()),
        # enum value newer than the generated protocol -> ValueError
        (
            {
                "cookies": [
                    {
                        "name": "n",
                        "value": "v",
                        "domain": "d",
                        "path": "/",
                        "size": 2,
                        "httpOnly": False,
                        "secure": False,
                        "session": True,
                        "priority": "Medium",
                        "sourceScheme": "Secure",
                        "sourcePort": 443,
                        "expires": -1,
                        "sameSite": "SomeFutureValue",
                    }
                ]
            },
            lambda: cdp.storage.get_cookies(),
        ),
    ],
    ids=["missing-key", "unknown-enum"],
)
async def test_unparseable_reply_raises_and_listener_survives(
    fake_ws: Callable[[Responder], None], bad_result: Any, cmd_factory: Any
) -> None:
    bad_methods = {"Target.getTargetInfo", "Storage.getCookies"}

    def responder(command: dict[str, Any]) -> list[Any]:
        if command["method"] in bad_methods:
            return [reply(command, bad_result)]
        return [reply(command, default_result(command["method"]))]

    fake_ws(responder)
    conn = Connection("ws://fake/devtools/browser/x")
    try:
        await conn.aopen()
        listener = conn.listener
        with pytest.raises(Exception) as excinfo:
            await finish_within(conn.send(cmd_factory()))
        print("send raised:", type(excinfo.value).__name__, excinfo.value)
        assert not isinstance(excinfo.value, asyncio.TimeoutError)
        print("listener after:", listener_state(conn))
        # the same listener keeps serving the connection
        assert conn.listener is listener and listener_state(conn) == "running"
        assert conn.mapper == {}
        version = await finish_within(conn.send(cdp.browser.get_version()))
        assert version[0] == "1.3"
    finally:
        await conn.aclose()


async def test_custom_generator_that_raises_propagates(
    fake_ws: Callable[[Responder], None],
) -> None:
    fake_ws(lambda c: [reply(c, default_result(c["method"]))])

    def custom_cmd() -> Any:
        j = yield {"method": "Runtime.evaluate", "params": {"expression": "1"}}
        return j["notThere"]

    conn = Connection("ws://fake/devtools/browser/x")
    try:
        with pytest.raises(Exception) as excinfo:
            await finish_within(conn.send(custom_cmd()))
        print("custom send raised:", type(excinfo.value).__name__, excinfo.value)
        assert listener_state(conn) == "running"
    finally:
        await conn.aclose()


async def test_generator_that_does_not_stop_raises_protocol_exception(
    fake_ws: Callable[[Responder], None],
) -> None:
    fake_ws(lambda c: [reply(c, default_result(c["method"]))])

    def two_step_cmd() -> Any:
        yield {"method": "Runtime.evaluate", "params": {"expression": "1"}}
        yield {"method": "Runtime.evaluate", "params": {"expression": "2"}}

    conn = Connection("ws://fake/devtools/browser/x")
    try:
        with pytest.raises(ProtocolException, match="could not parse"):
            await finish_within(conn.send(two_step_cmd()))
        assert listener_state(conn) == "running"
    finally:
        await conn.aclose()


# --- B15.4: a handler that raises when called ---------------------------------


async def test_bad_handler_does_not_kill_listener(
    fake_ws: Callable[[Responder], None],
) -> None:
    def responder(command: dict[str, Any]) -> list[Any]:
        frames: list[Any] = []
        if command["method"] == "Browser.getVersion":
            frames.append(
                {
                    "method": "Target.targetCreated",
                    "params": {"targetInfo": dict(TARGET_INFO)},
                }
            )
        frames.append(reply(command, default_result(command["method"])))
        return frames

    fake_ws(responder)
    seen: list[Any] = []

    async def bad_handler() -> None:  # wrong arity: TypeError when called
        pass

    async def good_handler(event: Any) -> None:
        seen.append(event)

    conn = Connection("ws://fake/devtools/browser/x")
    conn.add_handler(cdp.target.TargetCreated, bad_handler)
    conn.add_handler(cdp.target.TargetCreated, good_handler)
    try:
        version = await finish_within(conn.send(cdp.browser.get_version()))
        assert version[0] == "1.3"
        # the handler registered after the bad one still runs
        for _ in range(50):
            if seen:
                break
            await asyncio.sleep(0.01)
        print("listener after:", listener_state(conn), "good handler calls:", len(seen))
        assert listener_state(conn) == "running"
        assert len(seen) == 1
    finally:
        await conn.aclose()


# --- SEED-L1: unexpected exception from _receive_message ---------------------


@pytest.mark.parametrize(
    "bad_frame",
    ["this is not json", RuntimeError("unexpected recv failure")],
    ids=["non-json-frame", "recv-raises"],
)
async def test_unexpected_receive_error_does_not_hang_send(
    fake_ws: Callable[[Responder], None], bad_frame: Any
) -> None:
    injected: list[Any] = []

    def responder(command: dict[str, Any]) -> list[Any]:
        frames = [reply(command, default_result(command["method"]))]
        if command["method"] == "Browser.getVersion" and not injected:
            injected.append(bad_frame)  # only once, in front of the first reply
            frames.insert(0, bad_frame)
        return frames

    fake_ws(responder)
    conn = Connection("ws://fake/devtools/browser/x")
    try:
        outcome: Any
        try:
            outcome = await finish_within(conn.send(cdp.browser.get_version()))
        except Exception as e:  # raising is fine, hanging is not
            outcome = e
        print("send outcome:", repr(outcome), "| listener:", listener_state(conn))
        # the connection is still usable afterwards
        version = await finish_within(conn.send(cdp.browser.get_version()))
        assert version[0] == "1.3"
    finally:
        await conn.aclose()


# --- A2.4: tab sends must revive the browser connection's listener -----------


async def test_tab_send_revives_dead_browser_listener(
    fake_ws: Callable[[Responder], None],
) -> None:
    fake_ws(lambda c: [reply(c, default_result(c["method"]))])
    browser_conn = Connection("ws://fake/devtools/browser/x")
    owner = types.SimpleNamespace(connection=browser_conn, config=None)
    tab = Connection(
        "ws://fake/devtools/page/T1",
        target=cdp.target.TargetInfo.from_json(dict(TARGET_INFO)),
        _owner=owner,  # type: ignore[arg-type]
    )
    try:
        remote, _ = await finish_within(tab.send(cdp.runtime.evaluate("1+1")))
        assert remote.value == 2 and tab.session_id == "S1"

        # the browser listener stops for some reason (any of the other Q1 paths)
        assert browser_conn.listener is not None
        browser_conn.listener.cancel()
        await asyncio.wait({browser_conn.listener.task}, timeout=1)  # type: ignore[arg-type]
        assert listener_state(browser_conn) == "stopped"

        remote, _ = await finish_within(tab.send(cdp.runtime.evaluate("1+1")))
        print("tab send ok; browser listener:", listener_state(browser_conn))
        assert remote.value == 2
    finally:
        await tab.aclose()
        await browser_conn.aclose()


async def test_tab_command_in_flight_when_browser_listener_breaks(
    fake_ws: Callable[[Responder], None],
) -> None:
    """Browser listener hits an unexpected receive error while a tab command is
    waiting: the tab command must fail (not hang) and the tab must recover."""
    state = {"inject": False}

    def responder(command: dict[str, Any]) -> list[Any]:
        frames: list[Any] = [reply(command, default_result(command["method"]))]
        if command.get("sessionId") and state["inject"]:
            state["inject"] = False
            return [RuntimeError("unexpected recv failure")] + frames
        return frames

    fake_ws(responder)
    browser_conn = Connection("ws://fake/devtools/browser/x")
    owner = types.SimpleNamespace(connection=browser_conn, config=None)
    tab = Connection(
        "ws://fake/devtools/page/T1",
        target=cdp.target.TargetInfo.from_json(dict(TARGET_INFO)),
        _owner=owner,  # type: ignore[arg-type]
    )
    try:
        await finish_within(tab.send(cdp.runtime.evaluate("1+1")))
        state["inject"] = True
        with pytest.raises(RuntimeError):
            await finish_within(tab.send(cdp.runtime.evaluate("1+1")))
        print("browser listener after error:", listener_state(browser_conn))
        remote, _ = await finish_within(tab.send(cdp.runtime.evaluate("1+1")))
        assert remote.value == 2
    finally:
        await tab.aclose()
        await browser_conn.aclose()
