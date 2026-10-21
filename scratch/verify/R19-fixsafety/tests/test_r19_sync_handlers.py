"""
R19 regression tests: sync event handlers run in a worker thread, so
Connection.feed_cdp() (documented as the non-async way to answer
Fetch.requestPaused) must still send the command, and sync callables that
return an awaitable must have it awaited.

Browser-free: a fake CDP peer (websockets server) answers every command with
an empty result and emits Fetch.requestPaused when Fetch.enable arrives.
"""

from __future__ import annotations

import asyncio
import json
import threading
from typing import Any

import pytest
import websockets
import websockets.asyncio.server

import zendriver
from zendriver import cdp
from zendriver.core.connection import Connection

print("zendriver imported from:", zendriver.__file__)

PAUSED_EVENT = {
    "method": "Fetch.requestPaused",
    "params": {
        "requestId": "interception-1",
        "request": {
            "url": "http://example.test/x",
            "method": "GET",
            "headers": {},
            "initialPriority": "High",
            "referrerPolicy": "no-referrer",
        },
        "frameId": "frame-1",
        "resourceType": "Document",
    },
}


class FakePeer:
    def __init__(self) -> None:
        self.methods: list[str] = []
        self.continued = asyncio.Event()
        self.server: Any = None

    async def handler(self, ws: Any) -> None:
        try:
            async for raw in ws:
                msg = json.loads(raw)
                self.methods.append(msg["method"])
                await ws.send(json.dumps({"id": msg["id"], "result": {}}))
                if msg["method"] == "Fetch.enable":
                    await ws.send(json.dumps(PAUSED_EVENT))
                if msg["method"] == "Fetch.continueRequest":
                    self.continued.set()
        except websockets.exceptions.ConnectionClosed:
            pass

    async def __aenter__(self) -> str:
        self.server = await websockets.asyncio.server.serve(
            self.handler, "127.0.0.1", 0
        )
        port = self.server.sockets[0].getsockname()[1]
        return f"ws://127.0.0.1:{port}"

    async def __aexit__(self, *exc: Any) -> None:
        self.server.close()
        await self.server.wait_closed()


async def _run(handler: Any, *, expect_continue: bool = True) -> FakePeer:
    peer = FakePeer()
    async with peer as url:
        conn = Connection(url)
        try:
            conn.add_handler(cdp.fetch.RequestPaused, handler)
            await asyncio.wait_for(conn.send(cdp.fetch.enable()), 5)
            if expect_continue:
                await asyncio.wait_for(peer.continued.wait(), 5)
        finally:
            await asyncio.wait_for(conn.aclose(), 5)
    return peer


async def test_feed_cdp_from_sync_handler_sends_command() -> None:
    threads: list[str] = []

    def on_paused(event: cdp.fetch.RequestPaused, connection: Connection) -> None:
        threads.append(threading.current_thread().name)
        connection.feed_cdp(cdp.fetch.continue_request(request_id=event.request_id))

    try:
        peer = await _run(on_paused)
    except asyncio.TimeoutError:
        pytest.fail(
            f"Fetch.continueRequest never sent; handler ran in threads {threads}"
        )
    assert "Fetch.continueRequest" in peer.methods


async def test_feed_cdp_from_async_handler_still_works() -> None:
    async def on_paused(
        event: cdp.fetch.RequestPaused, connection: Connection
    ) -> None:
        connection.feed_cdp(cdp.fetch.continue_request(request_id=event.request_id))

    peer = await _run(on_paused)
    assert "Fetch.continueRequest" in peer.methods


async def test_sync_handler_returning_coroutine_is_awaited() -> None:
    ran = asyncio.Event()
    holder: dict[str, Connection] = {}

    async def process(event: cdp.fetch.RequestPaused) -> None:
        ran.set()
        await holder["conn"].send(
            cdp.fetch.continue_request(request_id=event.request_id)
        )

    peer = FakePeer()
    async with peer as url:
        conn = Connection(url)
        holder["conn"] = conn
        try:
            conn.add_handler(cdp.fetch.RequestPaused, lambda e: process(e))
            await asyncio.wait_for(conn.send(cdp.fetch.enable()), 5)
            try:
                await asyncio.wait_for(ran.wait(), 3)
            except asyncio.TimeoutError:
                pytest.fail("coroutine returned by the lambda handler never ran")
            await asyncio.wait_for(peer.continued.wait(), 5)
        finally:
            await asyncio.wait_for(conn.aclose(), 5)


async def test_feed_cdp_outside_handler_on_loop_thread() -> None:
    # plain call from the loop thread, as before
    peer = FakePeer()
    async with peer as url:
        conn = Connection(url)
        try:
            await asyncio.wait_for(conn.send(cdp.fetch.enable()), 5)
            conn.feed_cdp(cdp.fetch.continue_request(request_id=cdp.fetch.RequestId("abc")))
            await asyncio.wait_for(peer.continued.wait(), 5)
        finally:
            await asyncio.wait_for(conn.aclose(), 5)


async def test_feed_cdp_from_foreign_thread_without_listener_raises() -> None:
    # a connection that was never opened has no loop to schedule on: the error
    # must surface to the caller instead of being swallowed
    conn = Connection("ws://127.0.0.1:1")
    err: list[BaseException] = []

    def call() -> None:
        gen = cdp.fetch.continue_request(request_id=cdp.fetch.RequestId("abc"))
        try:
            conn.feed_cdp(gen)
        except BaseException as e:  # noqa
            err.append(e)

    await asyncio.to_thread(call)
    assert err and isinstance(err[0], RuntimeError)
