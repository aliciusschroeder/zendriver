"""
R16 regression tests: Connection state after close, against an in-process fake CDP peer.

Run against the repo:      pytest <this file>
Run against the prototype: PYTHONPATH=<scratch>/pkg pytest <this file>
"""

import asyncio
import json
import types

import pytest
import websockets
import websockets.asyncio.server

import zendriver
from zendriver import cdp
from zendriver.core.connection import Connection, ProtocolException

print("zendriver imported from", zendriver.__file__)

TARGET_INFO = {
    "targetId": "T1",
    "type": "page",
    "title": "",
    "url": "about:blank",
    "attached": True,
    "canAccessOpener": False,
}


class FakeCDP:
    """
    a tiny CDP peer: replies to every command with a canned result, except the
    methods listed in `drop`. it can flood events, close the websocket and send
    Target.detachedFromTarget on request.
    """

    def __init__(self, drop=(), close_after_first_reply=False, handshake_delay=0.0):
        self.drop = set(drop)
        self.close_after_first_reply = close_after_first_reply
        self.handshake_delay = handshake_delay
        self.connections = 0
        self.open_connections = 0
        self.flood_session: str | None | bool = False
        self.close_now = asyncio.Event()
        self.detach_now = asyncio.Event()
        self.server = None
        self.url = ""

    async def _process_request(self, connection, request):
        if self.handshake_delay:
            await asyncio.sleep(self.handshake_delay)
        return None

    def result_for(self, method):
        if method == "Target.getTargetInfo":
            return {"targetInfo": TARGET_INFO}
        if method == "Target.attachToTarget":
            return {"sessionId": "S1"}
        return {}

    async def handler(self, ws):
        self.connections += 1
        self.open_connections += 1
        first_connection = self.connections == 1
        tasks = [
            asyncio.ensure_future(self._reader(ws, first_connection)),
            asyncio.ensure_future(self._flooder(ws)),
            asyncio.ensure_future(self._closer(ws)),
            asyncio.ensure_future(self._detacher(ws)),
        ]
        try:
            await ws.wait_closed()
        finally:
            for t in tasks:
                t.cancel()
            self.open_connections -= 1

    async def _reader(self, ws, first_connection):
        try:
            async for raw in ws:
                msg = json.loads(raw)
                if msg["method"] in self.drop:
                    continue
                reply = {"id": msg["id"], "result": self.result_for(msg["method"])}
                if "sessionId" in msg:
                    reply["sessionId"] = msg["sessionId"]
                await ws.send(json.dumps(reply))
                if self.close_after_first_reply and first_connection:
                    await ws.close()
                    return
        except websockets.exceptions.ConnectionClosed:
            pass

    async def _flooder(self, ws):
        try:
            while True:
                await asyncio.sleep(0.02)
                if self.flood_session is False:
                    continue
                ev = {"method": "Page.domContentEventFired", "params": {"timestamp": 1.0}}
                if self.flood_session is not None:
                    ev["sessionId"] = self.flood_session
                await ws.send(json.dumps(ev))
        except websockets.exceptions.ConnectionClosed:
            pass

    async def _closer(self, ws):
        await self.close_now.wait()
        await ws.close()

    async def _detacher(self, ws):
        await self.detach_now.wait()
        await ws.send(
            json.dumps(
                {
                    "method": "Target.detachedFromTarget",
                    "params": {"sessionId": "S1", "targetId": "T1"},
                }
            )
        )

    async def __aenter__(self):
        self.server = await websockets.asyncio.server.serve(
            self.handler, "127.0.0.1", 0, process_request=self._process_request
        )
        port = self.server.sockets[0].getsockname()[1]
        self.url = f"ws://127.0.0.1:{port}/devtools/browser/fake"
        return self

    async def __aexit__(self, *exc):
        self.server.close()
        await self.server.wait_closed()


async def _until(predicate, timeout=3.0):
    loop = asyncio.get_running_loop()
    end = loop.time() + timeout
    while not predicate():
        if loop.time() > end:
            return False
        await asyncio.sleep(0.02)
    return True


async def _close_quietly(*conns):
    for c in conns:
        try:
            await asyncio.wait_for(c.aclose(), 5)
        except Exception:
            pass


# --------------------------------------------------------------------- SEED-C1
async def test_peer_close_forgets_websocket_and_reconnects():
    async with FakeCDP(close_after_first_reply=True) as peer:
        conn = Connection(peer.url)
        try:
            await asyncio.wait_for(conn.send(cdp.target.get_target_info()), 5)
            # the peer closed the websocket after its first reply
            assert await _until(lambda: not conn.listener.running)
            assert conn.closed, "closed is False although the peer closed the websocket"
            # the next command must open a new websocket (as after aclose())
            info = await asyncio.wait_for(conn.send(cdp.target.get_target_info()), 5)
            assert info.target_id == "T1"
            assert peer.connections == 2
        finally:
            await _close_quietly(conn)


# --------------------------------------------------------------------- SEED-C2
async def test_aclose_during_connect_leaves_connection_closed():
    async with FakeCDP(handshake_delay=0.5) as peer:
        conn = Connection(peer.url)
        opener = asyncio.ensure_future(conn.aopen())
        try:
            await asyncio.sleep(0.15)
            assert conn.websocket is None  # connect is still in progress
            await asyncio.wait_for(conn.aclose(), 5)
            try:
                await asyncio.wait_for(opener, 5)
            except ProtocolException:
                pass
            await asyncio.sleep(0.2)
            assert conn.closed, "websocket was opened after aclose()"
            assert not (conn.listener and conn.listener.running)
            assert await _until(lambda: peer.open_connections == 0)
        finally:
            if not opener.done():
                opener.cancel()
            await _close_quietly(conn)


# --------------------------------------------------------------------- SEED-C3
async def test_cancelled_send_does_not_leave_transaction_in_mapper():
    async with FakeCDP(drop={"Runtime.evaluate"}) as peer:
        conn = Connection(peer.url)
        try:
            with pytest.raises(asyncio.TimeoutError):
                await asyncio.wait_for(conn.send(cdp.runtime.evaluate("1")), 0.3)
            await asyncio.sleep(0)
            assert conn.mapper == {}, f"leaked transactions: {conn.mapper}"
        finally:
            await _close_quietly(conn)


# ---------------------------------------------------------------------- B14.5
async def _assert_waiter_finishes(waiter):
    done, _ = await asyncio.wait({waiter}, timeout=3)
    if not done:
        waiter.print_stack()
        waiter.cancel()
        pytest.fail("Connection.wait() still pending 3s after its listener stopped")
    waiter.result()


async def test_wait_returns_when_websocket_closes_while_busy():
    async with FakeCDP() as peer:
        conn = Connection(peer.url)
        try:
            await asyncio.wait_for(conn.aopen(), 5)
            peer.flood_session = None  # browser level events, every 20ms
            waiter = asyncio.ensure_future(conn.wait())
            await asyncio.sleep(0.4)
            assert not waiter.done(), "precondition: listener should be busy"
            peer.close_now.set()
            await _assert_waiter_finishes(waiter)
        finally:
            await _close_quietly(conn)


async def test_wait_returns_when_session_is_detached_while_busy():
    async with FakeCDP() as peer:
        browser_conn = Connection(peer.url)
        owner = types.SimpleNamespace(connection=browser_conn, config=None)
        target = cdp.target.TargetInfo.from_json(TARGET_INFO)
        tab = Connection(peer.url, target=target, _owner=owner)  # type: ignore[arg-type]
        try:
            await asyncio.wait_for(tab.aopen(), 5)
            assert tab.session_id == "S1"
            peer.flood_session = "S1"  # events for the tab's session, every 20ms
            waiter = asyncio.ensure_future(tab.wait())
            await asyncio.sleep(0.4)
            assert not waiter.done(), "precondition: listener should be busy"
            peer.detach_now.set()  # e.g. the tab was closed
            assert await _until(lambda: tab.session_id is None)
            await _assert_waiter_finishes(waiter)
        finally:
            await _close_quietly(tab, browser_conn)


# ------------------------------------------------- SEED-C2, flat session variant
class SlowAttachCDP(FakeCDP):
    async def _reader(self, ws, first_connection):
        try:
            async for raw in ws:
                msg = json.loads(raw)
                self.methods = getattr(self, "methods", []) + [msg["method"]]
                asyncio.ensure_future(self._reply(ws, msg))
        except websockets.exceptions.ConnectionClosed:
            pass

    async def _reply(self, ws, msg):
        if msg["method"] == "Target.attachToTarget":
            await asyncio.sleep(0.5)
        reply = {"id": msg["id"], "result": self.result_for(msg["method"])}
        if "sessionId" in msg:
            reply["sessionId"] = msg["sessionId"]
        try:
            await ws.send(json.dumps(reply))
        except websockets.exceptions.ConnectionClosed:
            pass


async def test_tab_aclose_during_attach_leaves_session_detached():
    async with SlowAttachCDP() as peer:
        browser_conn = Connection(peer.url)
        owner = types.SimpleNamespace(connection=browser_conn, config=None)
        target = cdp.target.TargetInfo.from_json(TARGET_INFO)
        tab = Connection(peer.url, target=target, _owner=owner)  # type: ignore[arg-type]
        opener = asyncio.ensure_future(tab.aopen())
        try:
            await asyncio.sleep(0.2)
            assert tab.session_id is None  # attach is still in progress
            await asyncio.wait_for(tab.aclose(), 5)
            try:
                await asyncio.wait_for(opener, 5)
            except ProtocolException:
                pass
            assert tab.session_id is None, "session was attached after aclose()"
            assert "S1" not in browser_conn._sessions
        finally:
            if not opener.done():
                opener.cancel()
            await _close_quietly(tab, browser_conn)
