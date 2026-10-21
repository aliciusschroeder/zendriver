import asyncio

import zendriver
from zendriver import cdp
from zendriver.core.connection import Connection

from fakepeer import FakePeer

print("ZENDRIVER IMPORTED FROM", zendriver.__file__)


async def test_user_dom_handler_survives_internal_dom_disable() -> None:
    # tab.xpath() does send(dom.enable(), True) then disable_dom_agent() -> DOM.disable
    peer = FakePeer()
    conn = Connection(await peer.start())
    try:
        conn.add_handler(cdp.dom.DocumentUpdated, lambda e: None)
        await asyncio.wait_for(conn.send(cdp.page.reload()), 5)
        await asyncio.wait_for(conn.send(cdp.dom.enable(), True), 5)
        await asyncio.wait_for(conn.send(cdp.dom.disable()), 5)
        mark = len(peer.received)
        await asyncio.wait_for(conn.send(cdp.page.reload()), 5)
        print("after internal DOM enable/disable pair:", peer.methods[mark:])
        assert peer.methods[mark:] == ["DOM.enable", "Page.reload"]
    finally:
        await conn.aclose()
        await peer.stop()


async def test_user_fetch_handler_after_intercept_block() -> None:
    # a user handler relying on auto enable, then tab.intercept()'s setup/teardown
    peer = FakePeer()
    conn = Connection(await peer.start())
    try:
        conn.add_handler(cdp.fetch.RequestPaused, lambda e: None)
        await asyncio.wait_for(conn.send(cdp.page.reload()), 5)
        await asyncio.wait_for(
            conn.send(cdp.fetch.enable([cdp.fetch.RequestPattern(url_pattern="*/x")])), 5
        )
        await asyncio.wait_for(conn.send(cdp.fetch.disable()), 5)
        mark = len(peer.received)
        await asyncio.wait_for(conn.send(cdp.page.reload()), 5)
        print("after intercept-like enable/disable:", peer.methods[mark:])
        assert peer.methods[mark:] == ["Fetch.enable", "Page.reload"]
    finally:
        await conn.aclose()
        await peer.stop()
