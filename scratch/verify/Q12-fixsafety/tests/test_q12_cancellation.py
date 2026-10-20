"""Regression tests for Q12: broad excepts swallowing asyncio.CancelledError."""

import asyncio
import json
import sys
from typing import Any

import pytest
import websockets

import zendriver as zd
from zendriver import cdp
from zendriver.core.connection import Connection
from zendriver.core.element import Element
from zendriver.core.proxy import UpstreamProxy


def test_print_imported_copy() -> None:
    print(f"\nzendriver imported from {zd.__file__} (python {sys.version.split()[0]})")


class SilentEnableWebSocket:
    """Answers every command with an empty result, except Network.enable.

    ``block_send`` makes ``send`` of Network.enable block (as under websocket
    backpressure), so the enable never reaches the "browser". Otherwise the
    enable is accepted but never answered (as when the target is busy).
    """

    def __init__(self, block_send: bool = False) -> None:
        self.closed = False
        self.block_send = block_send
        self._replies: asyncio.Queue[str] = asyncio.Queue()
        self.enables_delivered = 0
        self.enable_pending = asyncio.Event()
        self.answer_enable = False

    async def send(self, message: str) -> None:
        msg = json.loads(message)
        if msg["method"] == "Network.enable" and not self.answer_enable:
            self.enable_pending.set()
            if self.block_send:
                await asyncio.Event().wait()
            self.enables_delivered += 1
            return
        if msg["method"] == "Network.enable":
            self.enables_delivered += 1
        self._replies.put_nowait(json.dumps({"id": msg["id"], "result": {}}))

    async def recv(self) -> str:
        return await self._replies.get()

    async def close(self) -> None:
        self.closed = True


async def _fake_connection(
    monkeypatch: pytest.MonkeyPatch, ws: SilentEnableWebSocket
) -> Connection:
    async def fake_connect(*args: Any, **kwargs: Any) -> SilentEnableWebSocket:
        return ws

    monkeypatch.setattr(websockets, "connect", fake_connect)
    connection = Connection("ws://fake/devtools/browser/fake")
    connection.add_handler(cdp.network.RequestWillBeSent, lambda event: None)
    return connection


async def _settle(task: "asyncio.Future[Any]", connection: Connection) -> None:
    if not task.done():
        task.print_stack()
    await connection.aclose()
    if not task.done():
        task.cancel()
    await asyncio.wait({task}, timeout=2)
    if task.done() and not task.cancelled():
        task.exception()


async def test_wait_for_timeout_during_domain_enable_is_honoured(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    ws = SilentEnableWebSocket()
    connection = await _fake_connection(monkeypatch, ws)
    task = asyncio.ensure_future(
        asyncio.wait_for(
            connection.send(cdp.target.set_discover_targets(discover=True)),
            timeout=0.3,
        )
    )
    try:
        done, _ = await asyncio.wait({task}, timeout=3)
        assert task in done, "send() kept running after its wait_for timeout"
        assert isinstance(task.exception(), asyncio.TimeoutError)
    finally:
        await _settle(task, connection)


async def test_cancel_during_domain_enable_cancels_send(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    ws = SilentEnableWebSocket()
    connection = await _fake_connection(monkeypatch, ws)
    task = asyncio.ensure_future(
        connection.send(cdp.target.set_discover_targets(discover=True))
    )
    try:
        await asyncio.wait_for(ws.enable_pending.wait(), timeout=3)
        task.cancel()
        done, _ = await asyncio.wait({task}, timeout=3)
        assert task in done, "send() ignored task.cancel()"
        assert task.cancelled()
    finally:
        await _settle(task, connection)


async def test_cancelled_domain_enable_is_retried_later(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # the enable is cancelled before it reached the browser: the domain must not
    # stay marked as enabled, or its events are never delivered afterwards
    ws = SilentEnableWebSocket(block_send=True)
    connection = await _fake_connection(monkeypatch, ws)
    task = asyncio.ensure_future(
        connection.send(cdp.target.set_discover_targets(discover=True))
    )
    try:
        await asyncio.wait_for(ws.enable_pending.wait(), timeout=3)
        task.cancel()
        done, _ = await asyncio.wait({task}, timeout=3)
        assert task in done and task.cancelled()
        assert ws.enables_delivered == 0

        ws.answer_enable = True
        await asyncio.wait_for(
            connection.send(cdp.target.set_discover_targets(discover=True)),
            timeout=3,
        )
        assert ws.enables_delivered == 1
        assert cdp.network in connection.enabled_domains
    finally:
        await _settle(task, connection)


class BusyPageTab:
    """Duck-typed Tab whose page never answers Runtime.callFunctionOn (flash)."""

    def __init__(self) -> None:
        self.flash_pending = asyncio.Event()

    async def send(self, cdp_obj: Any) -> Any:
        method = next(cdp_obj)["method"]
        if method == "DOM.resolveNode":
            return cdp.runtime.RemoteObject(
                type_="object", object_id=cdp.runtime.RemoteObjectId("obj-1")
            )
        if method == "DOM.getContentQuads":
            return [[0.0, 0.0, 10.0, 0.0, 10.0, 10.0, 0.0, 10.0]]
        if method == "Runtime.callFunctionOn":
            self.flash_pending.set()
            await asyncio.Event().wait()
        raise AssertionError(method)

    async def mouse_click(self, *args: Any, **kwargs: Any) -> None:
        pass


def _node(node_id: int, name: str, **extra: Any) -> dict[str, Any]:
    return {
        "nodeId": node_id,
        "backendNodeId": node_id,
        "nodeType": 1,
        "nodeName": name.upper(),
        "localName": name,
        "nodeValue": "",
        "attributes": [],
        **extra,
    }


def _element(tab: BusyPageTab) -> Element:
    button = _node(3, "button", parentId=2)
    tree = cdp.dom.Node.from_json(
        {**_node(1, "#document"), "children": [_node(2, "body", children=[button])]}
    )
    node = cdp.dom.Node.from_json(button)
    return Element(node, tab, tree)  # type: ignore[arg-type]


async def test_cancel_during_mouse_click_flash_is_not_swallowed() -> None:
    tab = BusyPageTab()
    element = _element(tab)
    continued: list[str] = []

    async def flow() -> None:
        await element.mouse_click()
        continued.append("ran past the cancellation")

    task = asyncio.ensure_future(flow())
    try:
        await asyncio.wait_for(tab.flash_pending.wait(), timeout=3)
        task.cancel()
        done, _ = await asyncio.wait({task}, timeout=3)
        assert task in done
        assert continued == []
        assert task.cancelled()
    finally:
        if not task.done():
            task.cancel()
            await asyncio.wait({task}, timeout=2)


async def test_wait_for_timeout_during_mouse_click_flash_raises() -> None:
    tab = BusyPageTab()
    element = _element(tab)
    task = asyncio.ensure_future(asyncio.wait_for(element.mouse_click(), timeout=0.3))
    try:
        done, _ = await asyncio.wait({task}, timeout=3)
        assert task in done
        assert isinstance(task.exception(), asyncio.TimeoutError)
    finally:
        if not task.done():
            task.cancel()
            await asyncio.wait({task}, timeout=2)


async def test_open_tunnel_propagates_cancellation() -> None:
    # SEED-X3: the BaseException handler in open_tunnel re-raises CancelledError
    accepted = asyncio.Event()
    server_writers: list[asyncio.StreamWriter] = []

    async def silent_proxy(
        reader: asyncio.StreamReader, writer: asyncio.StreamWriter
    ) -> None:
        server_writers.append(writer)
        accepted.set()
        await reader.read()  # never answers the CONNECT

    server = await asyncio.start_server(silent_proxy, "127.0.0.1", 0)
    port = server.sockets[0].getsockname()[1]
    proxy = UpstreamProxy.from_url(f"http://u:p@127.0.0.1:{port}")
    assert proxy is not None
    task = asyncio.ensure_future(proxy.open_tunnel("example.com", 443))
    try:
        await asyncio.wait_for(accepted.wait(), timeout=3)
        await asyncio.sleep(0.05)
        task.cancel()
        done, _ = await asyncio.wait({task}, timeout=3)
        assert task in done and task.cancelled()
    finally:
        if not task.done():
            task.cancel()
        for w in server_writers:
            w.close()
        server.close()
        await server.wait_closed()
