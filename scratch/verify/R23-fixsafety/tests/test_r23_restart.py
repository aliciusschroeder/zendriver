"""
R23 regression tests: restarting a Browser, and the state of a Browser connected to
through host and port.

restart tests use real chromium (the bug is that chrome is never relaunched); the
host/port tests use a fake CDP peer (http /json/version + websocket on one port).
"""

import asyncio
import http
import json
import sys
import warnings

import asyncio_atexit
import pytest
from websockets.asyncio.server import serve

import zendriver as zd

print("zendriver imported from", zd.__file__, "python", sys.version.split()[0])


def _atexit_callbacks() -> list:
    return list(asyncio_atexit._get_entry().callbacks)


# --------------------------------------------------------------------------- restart


async def test_start_after_stop_launches_a_new_browser() -> None:
    browser = await zd.start(headless=True)
    try:
        first_pid = browser._process_pid
        first_port = browser.config.port
        await browser.stop()

        await asyncio.wait_for(browser.start(), 60)

        assert browser._process is not None and browser._process.poll() is None
        assert browser._process_pid != first_pid
        assert not browser.stopped
        # every tab is a target of the new browser, so navigating works
        page = await asyncio.wait_for(browser.get("about:blank"), 30)
        assert page in browser.tabs
        assert await asyncio.wait_for(page.evaluate("1 + 1"), 30) == 2
        # a restarted browser is stopped when the loop closes, exactly once
        assert _atexit_callbacks().count(browser._atexit_cleanup) == 1
        print("first port", first_port, "restart port", browser.config.port)
    finally:
        await asyncio.wait_for(browser.stop(), 30)
    assert browser.stopped
    assert browser._atexit_cleanup not in _atexit_callbacks()


async def test_start_after_the_browser_died_launches_a_new_browser() -> None:
    browser = await zd.start(headless=True)
    try:
        assert browser._process is not None
        first_pid = browser._process_pid
        browser._process.kill()
        await asyncio.to_thread(browser._process.wait)
        assert browser.stopped

        restarted = await asyncio.wait_for(browser.start(), 60)

        assert restarted is browser
        assert browser._process is not None and browser._process.poll() is None
        assert browser._process_pid != first_pid
        page = await asyncio.wait_for(browser.get("about:blank"), 30)
        assert await asyncio.wait_for(page.evaluate("1 + 1"), 30) == 2
        assert _atexit_callbacks().count(browser._atexit_cleanup) == 1
    finally:
        await asyncio.wait_for(browser.stop(), 30)
    assert browser.stopped


# ------------------------------------------------------------------- host and port


class FakeChrome:
    """answers /json/version over http and CDP commands over the websocket"""

    def __init__(self) -> None:
        self.open_websockets: set = set()
        self.port = 0

    def _process_request(self, connection, request):  # type: ignore[no-untyped-def]
        if request.path.startswith("/json"):
            body = json.dumps(
                {
                    "Browser": "FakeChrome/1.0",
                    "Protocol-Version": "1.3",
                    "User-Agent": "Mozilla/5.0 FakeChrome",
                    "webSocketDebuggerUrl": f"ws://127.0.0.1:{self.port}/devtools/browser/fake",
                }
            )
            return connection.respond(http.HTTPStatus.OK, body)
        return None

    async def _handler(self, websocket) -> None:  # type: ignore[no-untyped-def]
        self.open_websockets.add(websocket)
        try:
            async for raw in websocket:
                message = json.loads(raw)
                result: dict = {}
                if message["method"] == "Target.getTargets":
                    result = {"targetInfos": []}
                await websocket.send(json.dumps({"id": message["id"], "result": result}))
        except Exception:
            pass
        finally:
            self.open_websockets.discard(websocket)

    async def __aenter__(self) -> "FakeChrome":
        self.server = await serve(
            self._handler, "127.0.0.1", 0, process_request=self._process_request
        )
        self.port = self.server.sockets[0].getsockname()[1]
        return self

    async def __aexit__(self, *exc: object) -> None:
        self.server.close()
        await self.server.wait_closed()


async def _settle() -> None:
    for _ in range(20):
        await asyncio.sleep(0.05)


async def test_browser_connected_through_host_and_port_is_not_stopped() -> None:
    async with FakeChrome() as chrome:
        browser = await asyncio.wait_for(
            zd.start(host="127.0.0.1", port=chrome.port, headless=False), 30
        )
        try:
            assert browser._process is None
            assert not browser.stopped
        finally:
            await asyncio.wait_for(browser.stop(), 30)
        assert browser.stopped


async def test_second_start_of_a_connected_browser_keeps_its_connection() -> None:
    async with FakeChrome() as chrome:
        browser = await asyncio.wait_for(
            zd.start(host="127.0.0.1", port=chrome.port, headless=False), 30
        )
        try:
            first_connection = browser.connection
            await _settle()
            assert len(chrome.open_websockets) == 1

            with warnings.catch_warnings(record=True) as caught:
                warnings.simplefilter("always")
                await asyncio.wait_for(browser.start(), 30)
            await _settle()

            print("warnings:", [str(w.message) for w in caught])
            # either the call is ignored or the first connection is closed: never two
            assert len(chrome.open_websockets) == 1, chrome.open_websockets
            assert browser.connection is first_connection
            assert any("no effect" in str(w.message) for w in caught)
        finally:
            await asyncio.wait_for(browser.stop(), 30)
        await _settle()
        assert len(chrome.open_websockets) == 0


async def test_connected_browser_reconnects_after_stop() -> None:
    # non-regression: stop() then start() of a connected browser connects again
    async with FakeChrome() as chrome:
        browser = await asyncio.wait_for(
            zd.start(host="127.0.0.1", port=chrome.port, headless=False), 30
        )
        try:
            await browser.stop()
            assert browser.stopped
            await asyncio.wait_for(browser.start(), 30)
            assert not browser.stopped
            assert browser.config.host == "127.0.0.1"
            assert browser.config.port == chrome.port
            await _settle()
            assert len(chrome.open_websockets) == 1
        finally:
            await asyncio.wait_for(browser.stop(), 30)
