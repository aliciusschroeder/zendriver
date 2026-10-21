"""
R18 regression tests: the one-time expert/headless preparation of a flat session.

browser-free: websockets.connect is patched to return a fake browser websocket that
speaks flat sessions (Target.attachToTarget hands out session ids).
"""

import asyncio
import itertools
import json
import types
from typing import Any

import pytest
import websockets

import zendriver as zd
from zendriver.core.connection import Connection, Listener, ProtocolException

print("zendriver imported from", zd.__file__)

PAGE_SCOPED = ("Page.", "Network.", "Runtime.", "Emulation.")


class FakeBrowserSocket:
    """
    a browser websocket carrying flat sessions.

    :param delayed: session scoped methods whose reply is held back for a while
    :param detach_on: session scoped methods on which the session is detached by the
        browser (Target.detachedFromTarget) instead of being answered, for the first
        session only
    """

    def __init__(
        self, delayed: frozenset[str] = frozenset(), detach_on: frozenset[str] = frozenset()
    ) -> None:
        self.closed = False
        self.calls: list[tuple[str | None, str]] = []
        self._incoming: asyncio.Queue[str] = asyncio.Queue()
        self._session_ids = itertools.count(1)
        self._delayed = delayed
        self._detach_on = detach_on
        self._detached: set[str] = set()
        self._tasks: set[asyncio.Task[None]] = set()

    def calls_of(self, method: str, session_id: str | None = None) -> int:
        return sum(
            1
            for sid, m in self.calls
            if m == method and (sid == session_id if session_id else sid is not None)
        )

    async def send(self, message: str) -> None:
        msg = json.loads(message)
        sid = msg.get("sessionId")
        method = msg["method"]
        self.calls.append((sid, method))
        reply: dict[str, Any] = {"id": msg["id"]}
        if sid is not None:
            reply["sessionId"] = sid
        if method == "Target.attachToTarget":
            reply["result"] = {"sessionId": f"S{next(self._session_ids)}"}
        elif sid is None and method.startswith(PAGE_SCOPED):
            reply["error"] = {"code": -32601, "message": f"'{method}' wasn't found"}
        elif method == "Runtime.evaluate":
            reply["result"] = {"result": {"type": "number", "value": 1}}
        elif method == "Page.addScriptToEvaluateOnNewDocument":
            reply["result"] = {"identifier": str(len(self.calls))}
        else:
            reply["result"] = {}

        if sid is not None and method in self._detach_on and not self._detached:
            self._detached.add(sid)
            self._incoming.put_nowait(
                json.dumps(
                    {
                        "method": "Target.detachedFromTarget",
                        "params": {"sessionId": sid, "targetId": "T1"},
                    }
                )
            )
            return
        if sid is not None and method in self._delayed:
            task = asyncio.create_task(self._reply_later(json.dumps(reply)))
            self._tasks.add(task)
            task.add_done_callback(self._tasks.discard)
            return
        self._incoming.put_nowait(json.dumps(reply))

    async def _reply_later(self, message: str) -> None:
        await asyncio.sleep(0.05)
        self._incoming.put_nowait(message)

    async def recv(self) -> str:
        return await self._incoming.get()

    async def close(self) -> None:
        self.closed = True


def _make_tab(
    monkeypatch: pytest.MonkeyPatch,
    socket: FakeBrowserSocket,
    *,
    expert: bool,
    headless: bool,
) -> tuple[Connection, Connection]:
    async def connect(*args: Any, **kwargs: Any) -> FakeBrowserSocket:
        return socket

    monkeypatch.setattr(websockets, "connect", connect)
    owner: Any = types.SimpleNamespace(
        config=types.SimpleNamespace(expert=expert, headless=headless),
        _headless_user_agent=(
            "Mozilla/5.0 (X11; Linux x86_64) Chrome/141.0.0.0 Safari/537.36",
            zd.cdp.emulation.UserAgentMetadata(
                platform="Linux",
                platform_version="",
                architecture="x86",
                model="",
                mobile=False,
            ),
        ),
        connection=None,
    )
    browser_connection = Connection("ws://fake/devtools/browser/x", _owner=owner)
    owner.connection = browser_connection
    target = zd.cdp.target.TargetInfo(
        target_id=zd.cdp.target.TargetID("T1"),
        type_="page",
        title="",
        url="about:blank",
        attached=False,
        can_access_opener=False,
    )
    tab = Connection("ws://fake/devtools/page/T1", target=target, _owner=owner)
    return browser_connection, tab


@pytest.mark.parametrize(
    "expert, headless, method",
    [
        (True, False, "Page.addScriptToEvaluateOnNewDocument"),
        (False, True, "Network.setUserAgentOverride"),
    ],
)
async def test_concurrent_first_sends_prepare_the_session_once(
    monkeypatch: pytest.MonkeyPatch, expert: bool, headless: bool, method: str
) -> None:
    print("zendriver imported from", zd.__file__)
    socket = FakeBrowserSocket(delayed=frozenset({method}))
    browser_connection, tab = _make_tab(
        monkeypatch, socket, expert=expert, headless=headless
    )
    try:
        await asyncio.wait_for(
            asyncio.gather(
                tab.send(zd.cdp.runtime.evaluate("1")),
                tab.send(zd.cdp.runtime.evaluate("2")),
                tab.send(zd.cdp.runtime.evaluate("3")),
            ),
            timeout=10,
        )
        # a second copy of the expert script makes attachShadow call itself
        assert socket.calls_of(method, "S1") == 1, socket.calls
    finally:
        await tab.aclose()
        await browser_connection.aclose()


DETACH_CASES = pytest.mark.parametrize(
    "expert, headless, detach_on, method",
    [
        (False, True, "Network.setUserAgentOverride", "Network.setUserAgentOverride"),
        (True, False, "Page.enable", "Page.addScriptToEvaluateOnNewDocument"),
    ],
)


@DETACH_CASES
async def test_session_detached_while_being_prepared_is_prepared_after_reattach(
    monkeypatch: pytest.MonkeyPatch,
    expert: bool,
    headless: bool,
    detach_on: str,
    method: str,
) -> None:
    print("zendriver imported from", zd.__file__)
    socket = FakeBrowserSocket(detach_on=frozenset({detach_on}))
    browser_connection, tab = _make_tab(
        monkeypatch, socket, expert=expert, headless=headless
    )
    try:
        with pytest.raises(ProtocolException, match="detached"):
            await asyncio.wait_for(tab.send(zd.cdp.runtime.evaluate("1")), timeout=10)
        assert tab.session_id is None

        await asyncio.wait_for(tab.send(zd.cdp.runtime.evaluate("2")), timeout=10)
        assert tab.session_id == "S2"
        # the reattached session gets its user agent override / expert script too
        assert socket.calls_of(method, "S2") == 1, socket.calls
    finally:
        await tab.aclose()
        await browser_connection.aclose()


@DETACH_CASES
async def test_send_on_session_detached_while_being_prepared_leaves_nothing_behind(
    monkeypatch: pytest.MonkeyPatch,
    expert: bool,
    headless: bool,
    detach_on: str,
    method: str,
) -> None:
    print("zendriver imported from", zd.__file__)
    socket = FakeBrowserSocket(detach_on=frozenset({detach_on}))
    browser_connection, tab = _make_tab(
        monkeypatch, socket, expert=expert, headless=headless
    )
    detached_listeners: list[Listener] = []
    listener_init = Listener.__init__

    def tracking_listener_init(self: Listener, connection: Connection) -> None:
        if connection is tab and connection.websocket is None:
            detached_listeners.append(self)
        listener_init(self, connection)

    monkeypatch.setattr(Listener, "__init__", tracking_listener_init)
    try:
        with pytest.raises(ProtocolException, match="detached"):
            await asyncio.wait_for(tab.send(zd.cdp.runtime.evaluate("1")), timeout=10)
        # no listener started on the detached session, no command left behind
        await asyncio.sleep(0)
        for listener in detached_listeners:
            if listener.task and listener.task.done() and not listener.task.cancelled():
                print("listener on detached session died with", repr(listener.task.exception()))
        print("left in mapper:", tab.mapper)
        assert (detached_listeners, tab.mapper) == ([], {})
    finally:
        for listener in detached_listeners:
            listener.cancel()
        await tab.aclose()
        await browser_connection.aclose()
