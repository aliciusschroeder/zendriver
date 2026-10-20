"""
Regression tests for Q7: Connection._register_handlers reuses its snapshot of
enabled_domains after a nested send (domain.enable(), _is_update=True) has run
another _register_handlers that already pruned the stale domain.

Browser-free: an in-process websockets server plays the CDP peer.
"""

import asyncio
import json
from typing import Any

import pytest
import websockets
import websockets.asyncio.server

import zendriver
from zendriver import cdp
from zendriver.core.connection import Connection, ProtocolException

print("zendriver imported from:", zendriver.__file__)


class FakePeer:
    def __init__(self, fail_methods: set[str] | None = None) -> None:
        self.methods: list[str] = []
        self.fail_methods = fail_methods or set()
        self.server: Any = None

    async def handler(self, ws: Any) -> None:
        async for raw in ws:
            msg = json.loads(raw)
            self.methods.append(msg["method"])
            if msg["method"] in self.fail_methods:
                reply: dict[str, Any] = {
                    "id": msg["id"],
                    "error": {"code": -32000, "message": "nope"},
                }
            else:
                reply = {"id": msg["id"], "result": {}}
            await ws.send(json.dumps(reply))

    async def __aenter__(self) -> "FakePeer":
        self.server = await websockets.asyncio.server.serve(
            self.handler, "127.0.0.1", 0
        )
        return self

    async def __aexit__(self, *exc: Any) -> None:
        self.server.close()
        await self.server.wait_closed()

    @property
    def url(self) -> str:
        host, port = self.server.sockets[0].getsockname()[:2]
        return f"ws://{host}:{port}/devtools/page/FAKE"


async def _auto_enable_network_then_swap(
    conn: Connection, new_event: type
) -> None:
    def h1(ev: Any) -> None:
        pass

    def h2(ev: Any) -> None:
        pass

    conn.add_handler(cdp.network.RequestWillBeSent, h1)
    await asyncio.wait_for(conn.send(cdp.page.bring_to_front()), 10)
    assert conn.enabled_domains == [cdp.network]
    # the network handler goes away (e.g. expect_request's cleanup) ...
    conn.remove_handlers(cdp.network.RequestWillBeSent, h1)
    # ... and a handler for a domain that is not enabled yet is added
    conn.add_handler(new_event, h2)


@pytest.mark.parametrize(
    "new_event",
    [cdp.log.EntryAdded, cdp.page.LoadEventFired, cdp.runtime.ConsoleAPICalled],
)
async def test_send_after_stale_domain_and_new_handler_domain(
    new_event: type,
) -> None:
    async with FakePeer() as peer:
        conn = Connection(peer.url)
        try:
            await _auto_enable_network_then_swap(conn, new_event)
            new_domain = zendriver.core.util.cdp_get_module(new_event.__module__)
            peer.methods.clear()

            # must not raise ValueError: list.remove(x): x not in list
            await asyncio.wait_for(conn.send(cdp.page.bring_to_front()), 10)

            assert "Page.bringToFront" in peer.methods  # user command was sent
            assert conn.enabled_domains == [new_domain]
            # and things keep working
            await asyncio.wait_for(conn.send(cdp.page.bring_to_front()), 10)
            assert conn.enabled_domains == [new_domain]
        finally:
            await conn.aclose()


async def test_send_after_stale_domain_when_new_domain_enable_fails() -> None:
    async with FakePeer(fail_methods={"Log.enable"}) as peer:
        conn = Connection(peer.url)
        try:
            await _auto_enable_network_then_swap(conn, cdp.log.EntryAdded)
            peer.methods.clear()

            await asyncio.wait_for(conn.send(cdp.page.bring_to_front()), 10)

            assert "Page.bringToFront" in peer.methods
            assert cdp.network not in conn.enabled_domains
            assert cdp.log not in conn.enabled_domains
        finally:
            await conn.aclose()


async def test_concurrent_sends_with_stale_domain() -> None:
    async with FakePeer() as peer:
        conn = Connection(peer.url)
        try:
            await _auto_enable_network_then_swap(conn, cdp.log.EntryAdded)
            peer.methods.clear()

            results = await asyncio.wait_for(
                asyncio.gather(
                    conn.send(cdp.page.bring_to_front()),
                    conn.send(cdp.page.bring_to_front()),
                    return_exceptions=True,
                ),
                10,
            )
            assert [r for r in results if isinstance(r, BaseException)] == []
            assert peer.methods.count("Page.bringToFront") == 2
            assert conn.enabled_domains == [cdp.log]
        finally:
            await conn.aclose()


async def test_still_prunes_stale_domain_without_nesting() -> None:
    """behaviour that must be kept: an unused auto enabled domain is pruned."""
    async with FakePeer() as peer:
        conn = Connection(peer.url)
        try:

            def h1(ev: Any) -> None:
                pass

            conn.add_handler(cdp.network.RequestWillBeSent, h1)
            await asyncio.wait_for(conn.send(cdp.page.bring_to_front()), 10)
            assert conn.enabled_domains == [cdp.network]
            conn.remove_handlers(cdp.network.RequestWillBeSent, h1)
            await asyncio.wait_for(conn.send(cdp.page.bring_to_front()), 10)
            assert conn.enabled_domains == []
            # re adding the handler enables the domain again
            peer.methods.clear()
            conn.add_handler(cdp.network.RequestWillBeSent, h1)
            await asyncio.wait_for(conn.send(cdp.page.bring_to_front()), 10)
            assert conn.enabled_domains == [cdp.network]
            assert peer.methods.count("Network.enable") == 1
        finally:
            await conn.aclose()


async def test_manual_enable_keeps_manual_bookkeeping() -> None:
    async with FakePeer() as peer:
        conn = Connection(peer.url)
        try:

            def h1(ev: Any) -> None:
                pass

            conn.add_handler(cdp.network.RequestWillBeSent, h1)
            await asyncio.wait_for(conn.send(cdp.page.bring_to_front()), 10)
            await asyncio.wait_for(conn.send(cdp.network.enable()), 10)
            assert conn.manually_enabled_domains == [cdp.network]
            conn.remove_handlers(cdp.network.RequestWillBeSent, h1)
            conn.add_handler(cdp.log.EntryAdded, h1)
            await asyncio.wait_for(conn.send(cdp.page.bring_to_front()), 10)
            assert conn.manually_enabled_domains == [cdp.network]
            assert conn.enabled_domains == [cdp.log]
        finally:
            await conn.aclose()
