import asyncio
from collections.abc import Generator
from typing import Any, Union

import pytest

import zendriver as zd
from zendriver.core.connection import Connection
from zendriver.core.expect import (
    DownloadExpectation,
    RequestExpectation,
    ResponseExpectation,
)

IMAGE_PATTERN = r".*/img-R\d\.png"


def request_will_be_sent(request_id: str) -> zd.cdp.network.RequestWillBeSent:
    return zd.cdp.network.RequestWillBeSent.from_json(
        {
            "requestId": request_id,
            "loaderId": "L",
            "documentURL": "http://test/page.html",
            "request": {
                "url": f"http://test/img-{request_id}.png",
                "method": "GET",
                "headers": {},
                "initialPriority": "Low",
                "referrerPolicy": "no-referrer",
            },
            "timestamp": 1.0,
            "wallTime": 1.0,
            "initiator": {"type": "parser"},
            "redirectHasExtraInfo": False,
        }
    )


def response_received(request_id: str) -> zd.cdp.network.ResponseReceived:
    return zd.cdp.network.ResponseReceived.from_json(
        {
            "requestId": request_id,
            "loaderId": "L",
            "timestamp": 1.0,
            "type": "Image",
            "response": {
                "url": f"http://test/img-{request_id}.png",
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
        }
    )


def loading_finished(request_id: str) -> zd.cdp.network.LoadingFinished:
    return zd.cdp.network.LoadingFinished.from_json(
        {"requestId": request_id, "timestamp": 1.0, "encodedDataLength": 1}
    )


async def dispatch(connection: Connection, *events: Any) -> list[Any]:
    """
    Run the registered handlers the way Listener.listener_loop does when it
    drains several buffered messages without yielding: one task per event and
    handler, all created before the first one runs and removes its handler.
    Returns what each handler task returned or raised.
    """
    tasks = [
        asyncio.create_task(handler(event))
        for event in events
        for handler in connection.handlers[type(event)]
    ]
    return await asyncio.wait_for(asyncio.gather(*tasks, return_exceptions=True), 5)


@pytest.mark.parametrize("expectation_class", [RequestExpectation, ResponseExpectation])
async def test_expectation_burst_keeps_first_matching_request(
    monkeypatch: pytest.MonkeyPatch,
    expectation_class: type[Union[RequestExpectation, ResponseExpectation]],
) -> None:
    connection = Connection("ws://unused")
    body_requests: list[str] = []

    async def send(
        cdp_obj: Generator[dict[str, Any], dict[str, Any], Any],
        _is_update: bool = False,
    ) -> Any:
        command = next(cdp_obj)
        assert command["method"] == "Network.getResponseBody"
        body_requests.append(command["params"]["requestId"])
        return f"body of {command['params']['requestId']}", False

    monkeypatch.setattr(connection, "send", send)

    async with expectation_class(connection, IMAGE_PATTERN) as expectation:
        results = await dispatch(
            connection, request_will_be_sent("R1"), request_will_be_sent("R2")
        )
        results += await dispatch(
            connection, response_received("R1"), response_received("R2")
        )
        results += await dispatch(
            connection, loading_finished("R1"), loading_finished("R2")
        )

        assert expectation.request_id == "R1"
        assert (await expectation.value).request_id == "R1"
        assert (await expectation.request).url == "http://test/img-R1.png"
        assert (await expectation.response).url == "http://test/img-R1.png"
        assert (await expectation.loading_finished_future).request_id == "R1"
        assert await expectation.response_body == ("body of R1", False)
        assert body_requests == ["R1"]
        assert results == [None] * 6


async def test_events_after_timed_out_waits_are_tracked_without_errors() -> None:
    """
    A timed out wait cancels the future it waited on. The events that arrive
    afterwards must still be tracked and must not raise InvalidStateError in
    the handler tasks.
    """
    connection = Connection("ws://unused")

    async with RequestExpectation(connection, IMAGE_PATTERN) as expectation:
        with pytest.raises(asyncio.TimeoutError):
            await asyncio.wait_for(expectation.value, 0.05)
        with pytest.raises(asyncio.TimeoutError):
            await asyncio.wait_for(expectation.response, 0.05)
        with pytest.raises(asyncio.TimeoutError):
            await asyncio.wait_for(expectation.loading_finished_future, 0.05)
        assert expectation.request_future.cancelled()
        assert expectation.response_future.cancelled()
        assert expectation.loading_finished_future.cancelled()

        results = await dispatch(
            connection,
            request_will_be_sent("R1"),
            response_received("R1"),
            loading_finished("R1"),
        )

        assert expectation.request_id == "R1"
        assert results == [None] * 3
        assert not connection.handlers[zd.cdp.network.ResponseReceived]
        assert not connection.handlers[zd.cdp.network.LoadingFinished]


async def test_download_expectation_burst_keeps_first_download() -> None:
    connection = Connection("ws://unused")
    expectation = DownloadExpectation(connection)
    connection.add_handler(zd.cdp.browser.DownloadWillBegin, expectation._handler)
    events = [
        zd.cdp.browser.DownloadWillBegin.from_json(
            {
                "frameId": "F",
                "guid": guid,
                "url": f"http://test/{guid}",
                "suggestedFilename": guid,
            }
        )
        for guid in ("G1", "G2")
    ]

    results = await dispatch(connection, *events)

    assert (await expectation.value).guid == "G1"
    assert results == [None, None]
