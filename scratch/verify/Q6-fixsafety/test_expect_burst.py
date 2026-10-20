import asyncio
import gc
import json
import sys
from typing import Any

import pytest
import websockets

import zendriver as zd
from zendriver.core.connection import Connection
from zendriver.core.expect import DownloadExpectation, RequestExpectation

print("zendriver imported from:", zd.__file__, "| python", sys.version.split()[0])


def _request_will_be_sent(request_id: str, url: str) -> dict[str, Any]:
    return {
        "method": "Network.requestWillBeSent",
        "params": {
            "requestId": request_id,
            "loaderId": "L1",
            "documentURL": "http://test/page.html",
            "request": {
                "url": url,
                "method": "GET",
                "headers": {},
                "initialPriority": "Low",
                "referrerPolicy": "no-referrer",
            },
            "timestamp": 1.0,
            "wallTime": 1.0,
            "initiator": {"type": "parser"},
            "redirectHasExtraInfo": False,
        },
    }


def _response_received(request_id: str, url: str) -> dict[str, Any]:
    return {
        "method": "Network.responseReceived",
        "params": {
            "requestId": request_id,
            "loaderId": "L1",
            "timestamp": 1.0,
            "type": "Image",
            "response": {
                "url": url,
                "status": 200,
                "statusText": "OK",
                "headers": {},
                "mimeType": "image/png",
                "charset": "",
                "connectionReused": False,
                "connectionId": 1,
                "encodedDataLength": 1,
                "securityState": "neutral",
            },
            "hasExtraInfo": False,
        },
    }


def _loading_finished(request_id: str) -> dict[str, Any]:
    return {
        "method": "Network.loadingFinished",
        "params": {"requestId": request_id, "timestamp": 1.0, "encodedDataLength": 1},
    }


class BurstWebSocket:
    """Replies to every command with an empty result; events can be queued in bursts."""

    def __init__(self) -> None:
        self.closed = False
        self._messages: asyncio.Queue[str] = asyncio.Queue()

    def burst(self, messages: list[dict[str, Any]]) -> None:
        for message in messages:
            self._messages.put_nowait(json.dumps(message))

    async def send(self, message: str) -> None:
        self._messages.put_nowait(
            json.dumps({"id": json.loads(message)["id"], "result": {}})
        )

    async def recv(self) -> str:
        return await self._messages.get()

    async def close(self) -> None:
        self.closed = True


@pytest.fixture
async def unhandled_task_errors() -> Any:
    loop = asyncio.get_running_loop()
    errors: list[BaseException | None] = []
    previous = loop.get_exception_handler()
    loop.set_exception_handler(lambda _, ctx: errors.append(ctx.get("exception")))
    yield errors
    loop.set_exception_handler(previous)


async def _collect_lost_task_errors() -> None:
    await asyncio.sleep(0.05)
    gc.collect()


async def test_expect_request_burst_keeps_first_request(
    monkeypatch: pytest.MonkeyPatch, unhandled_task_errors: list[Any]
) -> None:
    websocket = BurstWebSocket()

    async def fake_connect(*args: Any, **kwargs: Any) -> BurstWebSocket:
        return websocket

    monkeypatch.setattr(websockets, "connect", fake_connect)
    connection = Connection("ws://fake/devtools/page/fake")
    try:
        async with RequestExpectation(connection, r".*/img\d\.png") as expectation:
            # opens the fake websocket, starts the listener and enables Network
            await asyncio.wait_for(connection.send(zd.cdp.page.enable()), 5)
            ids = [f"R{i}" for i in range(3)]
            urls = [f"http://test/img{i}.png" for i in range(3)]
            websocket.burst(
                [_request_will_be_sent(i, u) for i, u in zip(ids, urls)]
                + [_response_received(i, u) for i, u in zip(ids, urls)]
                + [_loading_finished(i) for i in ids]
            )
            request = await asyncio.wait_for(expectation.value, 5)
            response = await asyncio.wait_for(expectation.response_future, 5)
            finished = await asyncio.wait_for(expectation.loading_finished_future, 5)
            await _collect_lost_task_errors()
            print(
                "request:", request.request.url,
                "| response:", response.response.url,
                "| loadingFinished:", finished.request_id,
                "| lost task errors:", unhandled_task_errors,
            )

            assert request.request.url == urls[0]
            assert expectation.request_id == ids[0]
            assert response.request_id == ids[0]
            assert response.response.url == urls[0]
            assert finished.request_id == ids[0]
            assert unhandled_task_errors == []
    finally:
        await connection.aclose()


async def test_request_handler_dispatched_twice_keeps_first_request(
    unhandled_task_errors: list[Any],
) -> None:
    """the Listener create_task()s one handler call per event; several can be
    scheduled before the first one runs and removes the handler"""
    connection = Connection("ws://unused")
    expectation = RequestExpectation(connection, r".*/img\d\.png")
    await expectation._setup()
    first = zd.cdp.network.RequestWillBeSent.from_json(
        _request_will_be_sent("R0", "http://test/img0.png")["params"]
    )
    second = zd.cdp.network.RequestWillBeSent.from_json(
        _request_will_be_sent("R1", "http://test/img1.png")["params"]
    )
    tasks = [
        asyncio.create_task(expectation._request_handler(first)),
        asyncio.create_task(expectation._request_handler(second)),
    ]
    results = await asyncio.wait_for(
        asyncio.gather(*tasks, return_exceptions=True), 5
    )
    response = zd.cdp.network.ResponseReceived.from_json(
        _response_received("R1", "http://test/img1.png")["params"]
    )
    await expectation._response_handler(response)

    assert results == [None, None]
    assert (await expectation.value).request_id == "R0"
    assert expectation.request_id == "R0"
    assert not expectation.response_future.done()


async def test_download_handler_dispatched_twice(
    unhandled_task_errors: list[Any],
) -> None:
    connection = Connection("ws://unused")
    expectation = DownloadExpectation(connection)
    connection.add_handler(zd.cdp.browser.DownloadWillBegin, expectation._handler)
    events = [
        zd.cdp.browser.DownloadWillBegin.from_json(
            {"frameId": "F", "guid": f"G{i}", "url": f"http://x/{i}", "suggestedFilename": "f"}
        )
        for i in range(2)
    ]
    results = await asyncio.wait_for(
        asyncio.gather(
            *(asyncio.create_task(expectation._handler(e)) for e in events),
            return_exceptions=True,
        ),
        5,
    )
    assert results == [None, None]
    assert (await expectation.value).guid == "G0"


async def test_response_still_resolves_after_timed_out_wait_for_request(
    monkeypatch: pytest.MonkeyPatch, unhandled_task_errors: list[Any]
) -> None:
    """a timed out wait_for(expectation.value) cancels request_future; the
    response of the next matching request must still be tracked"""
    websocket = BurstWebSocket()

    async def fake_connect(*args: Any, **kwargs: Any) -> BurstWebSocket:
        return websocket

    monkeypatch.setattr(websockets, "connect", fake_connect)
    connection = Connection("ws://fake/devtools/page/fake")
    try:
        async with RequestExpectation(connection, r".*/img\d\.png") as expectation:
            await asyncio.wait_for(connection.send(zd.cdp.page.enable()), 5)
            with pytest.raises(asyncio.TimeoutError):
                await asyncio.wait_for(expectation.value, 0.05)
            assert expectation.request_future.cancelled()
            websocket.burst(
                [
                    _request_will_be_sent("R0", "http://test/img0.png"),
                    _response_received("R0", "http://test/img0.png"),
                ]
            )
            response = await asyncio.wait_for(expectation.response_future, 2)
            await _collect_lost_task_errors()
            assert response.request_id == "R0"
            assert unhandled_task_errors == []
    finally:
        await connection.aclose()
