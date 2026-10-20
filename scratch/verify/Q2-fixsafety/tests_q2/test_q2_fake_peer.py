"""
Q2 over a real websocket: a fake CDP peer that never answers DOM.* (renderer
blocked by a dialog).  The second test registers a handler for a DOM event, so
send() first goes through Connection._register_handlers -> DOM.enable, whose
bare `except:` swallows the timeout's CancelledError.
"""

from __future__ import annotations

import asyncio
import json
import time
from typing import Any, AsyncIterator

import pytest
import websockets

import zendriver as zd
from zendriver import cdp

SAFETY = 6


@pytest.fixture
async def blocked_peer() -> AsyncIterator[str]:
    async def handler(ws: Any) -> None:
        async for raw in ws:
            msg = json.loads(raw)
            if msg["method"].startswith("DOM."):
                continue  # the blocked renderer never answers
            await ws.send(json.dumps({"id": msg["id"], "result": {}}))

    server = await websockets.serve(handler, "127.0.0.1", 0)
    port = server.sockets[0].getsockname()[1]
    try:
        yield f"ws://127.0.0.1:{port}"
    finally:
        server.close()
        await server.wait_closed()


async def _close(tab: zd.Tab) -> None:
    try:
        await asyncio.wait_for(tab.aclose(), 3)
    except BaseException:  # noqa
        pass


async def test_select_times_out_over_websocket(blocked_peer: str) -> None:
    print("\nzendriver imported from", zd.__file__)
    tab = zd.Tab(blocked_peer, None)  # type: ignore[arg-type]
    try:
        t0 = time.monotonic()
        with pytest.raises(asyncio.TimeoutError, match="selector: '#x'"):
            await asyncio.wait_for(tab.select("#x", timeout=1), SAFETY)
        assert time.monotonic() - t0 < 2
    finally:
        await _close(tab)


async def test_select_times_out_with_pending_domain_enable(blocked_peer: str) -> None:
    tab = zd.Tab(blocked_peer, None)  # type: ignore[arg-type]
    tab.add_handler(cdp.dom.DocumentUpdated, lambda ev: None)
    try:
        t0 = time.monotonic()
        with pytest.raises(asyncio.TimeoutError, match="selector: '#x'"):
            await asyncio.wait_for(tab.select("#x", timeout=1), SAFETY)
        assert time.monotonic() - t0 < 2
    finally:
        await _close(tab)
