import asyncio
import gc
from typing import Any

import pytest

import zendriver
from zendriver import cdp
from zendriver.core.connection import Connection, ProtocolException
from zendriver.core.expect import RequestExpectation, ResponseExpectation

from fakepeer import FakePeer

print("ZENDRIVER IMPORTED FROM", zendriver.__file__)

URL = "http://x.test/page1"
REQ = {
    "url": URL,
    "method": "GET",
    "headers": {},
    "initialPriority": "High",
    "referrerPolicy": "no-referrer",
}
RESP = {
    "url": URL,
    "status": 200,
    "statusText": "OK",
    "headers": {},
    "mimeType": "text/html",
    "charset": "utf-8",
    "connectionReused": False,
    "connectionId": 1,
    "encodedDataLength": 10,
    "securityState": "neutral",
}


async def emit(peer: FakePeer, method: str, params: dict[str, Any]) -> None:
    # like chrome: Network events only flow once Network.enable was received
    if "Network.enable" in peer.methods:
        await peer.send_event(method, params)


async def will_be_sent(peer: FakePeer) -> None:
    await emit(
        peer,
        "Network.requestWillBeSent",
        {
            "requestId": "r1",
            "loaderId": "l1",
            "documentURL": URL,
            "request": REQ,
            "timestamp": 1.0,
            "wallTime": 1.0,
            "initiator": {"type": "script"},
            "redirectHasExtraInfo": False,
        },
    )


async def response_received(peer: FakePeer) -> None:
    await emit(
        peer,
        "Network.responseReceived",
        {
            "requestId": "r1",
            "loaderId": "l1",
            "timestamp": 1.1,
            "type": "Fetch",
            "response": RESP,
            "hasExtraInfo": False,
        },
    )


async def loading_failed(peer: FakePeer) -> None:
    await emit(
        peer,
        "Network.loadingFailed",
        {
            "requestId": "r1",
            "timestamp": 1.2,
            "type": "Fetch",
            "errorText": "net::ERR_CONTENT_LENGTH_MISMATCH",
            "canceled": False,
        },
    )


@pytest.fixture
async def peer_conn():  # type: ignore[no-untyped-def]
    loop_errors: list[Any] = []
    loop = asyncio.get_running_loop()
    loop.set_exception_handler(lambda _l, ctx: loop_errors.append(ctx))
    peer = FakePeer()
    conn = Connection(await peer.start())
    await asyncio.wait_for(conn.aopen(), 5)
    yield peer, conn, loop_errors
    await asyncio.wait_for(conn.aclose(), 5)
    await peer.stop()
    loop.set_exception_handler(None)


async def test_a10_3_timed_out_wait_does_not_kill_expectation(peer_conn) -> None:  # type: ignore[no-untyped-def]
    peer, conn, loop_errors = peer_conn
    async with ResponseExpectation(conn, r".*/page1") as exp:
        with pytest.raises(asyncio.TimeoutError):
            await asyncio.wait_for(exp.value, 0.2)
        await asyncio.wait_for(conn.send(cdp.page.reload()), 5)
        await will_be_sent(peer)
        await response_received(peer)
        got = await asyncio.wait_for(exp.value, 2)
        assert got.response.url == URL
    await asyncio.sleep(0.05)
    print("loop errors:", [c.get("exception") for c in loop_errors])
    assert not loop_errors


async def test_a10_7_network_enabled_on_enter(peer_conn) -> None:  # type: ignore[no-untyped-def]
    peer, conn, _ = peer_conn
    async with RequestExpectation(conn, r".*/page1") as r:
        print("sent before awaiting:", peer.methods)
        # the page starts the request itself: no command is sent by the user
        await will_be_sent(peer)
        got = await asyncio.wait_for(r.value, 2)
        assert got.request.url == URL


async def test_b13_7_body_of_request_failed_after_headers_raises(peer_conn) -> None:  # type: ignore[no-untyped-def]
    peer, conn, _ = peer_conn
    async with ResponseExpectation(conn, r".*/page1") as exp:
        await asyncio.wait_for(conn.send(cdp.page.reload()), 5)
        await will_be_sent(peer)
        await response_received(peer)
        await loading_failed(peer)
        assert (await asyncio.wait_for(exp.value, 2)).response.status == 200
        with pytest.raises(ProtocolException, match="ERR_CONTENT_LENGTH_MISMATCH"):
            await asyncio.wait_for(exp.response_body, 2)


async def test_b13_7_value_of_request_failed_before_response_raises(peer_conn) -> None:  # type: ignore[no-untyped-def]
    peer, conn, loop_errors = peer_conn
    async with ResponseExpectation(conn, r".*/page1") as exp:
        await asyncio.wait_for(conn.send(cdp.page.reload()), 5)
        await will_be_sent(peer)
        await loading_failed(peer)
        with pytest.raises(ProtocolException):
            await asyncio.wait_for(exp.value, 2)
    del exp
    gc.collect()
    await asyncio.sleep(0.05)
    print("loop errors:", [c.get("message") for c in loop_errors])
    assert not loop_errors
