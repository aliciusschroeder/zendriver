import asyncio

import zendriver
from zendriver import cdp
from zendriver.core.connection import Connection

from fakepeer import FakePeer

print("ZENDRIVER IMPORTED FROM", zendriver.__file__)


async def _setup() -> tuple[FakePeer, Connection]:
    peer = FakePeer()
    url = await peer.start()
    return peer, Connection(url)


async def _teardown(peer: FakePeer, conn: Connection) -> None:
    await asyncio.wait_for(conn.aclose(), 5)
    await peer.stop()


async def test_a12_2_removing_last_fetch_handler_disables_auto_enabled_fetch() -> None:
    peer, conn = await _setup()
    try:

        def h(event: cdp.fetch.RequestPaused) -> None:
            pass

        conn.add_handler(cdp.fetch.RequestPaused, h)
        await asyncio.wait_for(conn.send(cdp.page.reload()), 5)
        assert peer.methods == ["Fetch.enable", "Page.reload"]
        assert cdp.fetch in conn.enabled_domains

        conn.remove_handlers(cdp.fetch.RequestPaused, h)
        mark = len(peer.received)
        await asyncio.wait_for(conn.send(cdp.page.reload()), 5)
        after = peer.methods[mark:]
        print("sent after remove_handlers:", after, "enabled:", conn.enabled_domains)
        assert cdp.fetch not in conn.enabled_domains
        # the browser must be told: an auto enabled Fetch pauses every request
        assert after == ["Fetch.disable", "Page.reload"], after
    finally:
        await _teardown(peer, conn)


async def test_a12_2_network_is_not_disabled_when_handlers_go() -> None:
    # guard for the fix: Network.disable would drop buffered response bodies
    peer, conn = await _setup()
    try:

        def h(event: cdp.network.RequestWillBeSent) -> None:
            pass

        conn.add_handler(cdp.network.RequestWillBeSent, h)
        await asyncio.wait_for(conn.send(cdp.page.reload()), 5)
        conn.remove_handlers(cdp.network.RequestWillBeSent, h)
        mark = len(peer.received)
        await asyncio.wait_for(conn.send(cdp.page.reload()), 5)
        assert peer.methods[mark:] == ["Page.reload"]
    finally:
        await _teardown(peer, conn)


async def test_a2_2_manual_disable_is_not_undone_by_paramless_enable() -> None:
    peer, conn = await _setup()
    try:

        def h(event: cdp.fetch.RequestPaused) -> None:
            pass

        conn.add_handler(cdp.fetch.RequestPaused, h)
        await asyncio.wait_for(
            conn.send(
                cdp.fetch.enable(patterns=[cdp.fetch.RequestPattern(url_pattern="*/x")])
            ),
            5,
        )
        await asyncio.wait_for(conn.send(cdp.fetch.disable()), 5)
        mark = len(peer.received)
        await asyncio.wait_for(conn.send(cdp.page.reload()), 5)
        after = [(m["method"], m.get("params")) for m in peer.received[mark:]]
        print("sent after manual disable:", after)
        assert after == [("Page.reload", {})], after

        # once the handler is gone and a new one is added, auto enable works again
        conn.remove_handlers(cdp.fetch.RequestPaused, h)
        await asyncio.wait_for(conn.send(cdp.page.reload()), 5)
        conn.add_handler(cdp.fetch.RequestPaused, h)
        mark = len(peer.received)
        await asyncio.wait_for(conn.send(cdp.page.reload()), 5)
        assert peer.methods[mark:] == ["Fetch.enable", "Page.reload"]
    finally:
        await _teardown(peer, conn)
