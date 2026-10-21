"""R24: connecting to an existing browser (host + port) must not need a local browser binary."""

import asyncio
import json
from http import HTTPStatus
from types import SimpleNamespace
from typing import Any

import pytest
import websockets
from websockets.asyncio.server import serve

import zendriver as zd
import zendriver.core.config as zd_config
import zendriver.core.util as zd_util

print("zendriver imported from", zd.__file__)


def _no_local_browser(browser: Any = "auto") -> Any:
    raise FileNotFoundError(
        "could not find a valid browser binary. please make sure it is installed "
        "or use the keyword argument 'browser_executable_path=/path/to/your/browser' "
    )


@pytest.fixture
def no_local_browser(monkeypatch: pytest.MonkeyPatch) -> None:
    # simulate a machine (e.g. a slim container) without any chrome/brave/edge
    monkeypatch.setattr(zd_config, "find_executable", _no_local_browser)


class FakeDevTools:
    """minimal DevTools endpoint: /json/version over HTTP plus a CDP websocket"""

    def __init__(self) -> None:
        self.methods: list[str] = []
        self.port = 0

    def _process_request(self, connection: Any, request: Any) -> Any:
        if request.path == "/json/version":
            body = json.dumps(
                {
                    "Browser": "Chrome/141.0.0.0",
                    "Protocol-Version": "1.3",
                    "User-Agent": "Mozilla/5.0 Chrome/141.0.0.0",
                    "V8-Version": "14.1",
                    "WebKit-Version": "537.36",
                    "webSocketDebuggerUrl": f"ws://127.0.0.1:{self.port}/devtools/browser/fake",
                }
            )
            return connection.respond(HTTPStatus.OK, body)
        return None

    async def _handler(self, ws: Any) -> None:
        try:
            async for raw in ws:
                msg = json.loads(raw)
                self.methods.append(msg["method"])
                result: dict[str, Any] = {}
                if msg["method"] == "Target.getTargets":
                    result = {"targetInfos": []}
                await ws.send(json.dumps({"id": msg["id"], "result": result}))
        except websockets.ConnectionClosed:
            pass

    async def __aenter__(self) -> "FakeDevTools":
        self._server = await serve(
            self._handler, "127.0.0.1", 0, process_request=self._process_request
        )
        self.port = self._server.sockets[0].getsockname()[1]
        return self

    async def __aexit__(self, *exc: Any) -> None:
        self._server.close()
        await self._server.wait_closed()


def test_config_with_host_and_port_needs_no_local_browser(no_local_browser: None) -> None:
    config = zd.Config(host="127.0.0.1", port=9222)
    assert config.host == "127.0.0.1"
    assert config.port == 9222


def test_config_without_host_and_port_still_requires_a_browser(
    no_local_browser: None,
) -> None:
    with pytest.raises(FileNotFoundError):
        zd.Config()
    with pytest.raises(FileNotFoundError):
        zd.Config(host="127.0.0.1")


async def test_start_connects_to_existing_browser_without_local_browser(
    no_local_browser: None, tmp_path: Any
) -> None:
    async with FakeDevTools() as peer:
        browser = await asyncio.wait_for(
            zd.start(host="127.0.0.1", port=peer.port, user_data_dir=tmp_path), 10
        )
        try:
            assert "Target.setDiscoverTargets" in peer.methods
            assert browser._process is None
        finally:
            await asyncio.wait_for(browser.stop(), 10)


async def test_browser_create_connects_without_local_browser(
    no_local_browser: None, tmp_path: Any
) -> None:
    async with FakeDevTools() as peer:
        browser = await asyncio.wait_for(
            zd.Browser.create(host="127.0.0.1", port=peer.port, user_data_dir=tmp_path),
            10,
        )
        try:
            assert "Target.getTargets" in peer.methods
        finally:
            await asyncio.wait_for(browser.stop(), 10)


async def test_create_from_undetected_chromedriver_without_local_browser(
    no_local_browser: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    started: list[Any] = []

    async def fake_start(config: Any = None, **kwargs: Any) -> Any:
        started.append(config)
        return SimpleNamespace(_process_pid=None)

    monkeypatch.setattr(zd_util, "start", fake_start)
    stopped: list[bool] = []
    driver = SimpleNamespace(
        options=SimpleNamespace(debugger_address="127.0.0.1:9333"),
        browser_pid=4242,
        service=SimpleNamespace(stop=lambda: stopped.append(True)),
        user_data_dir="/tmp/whatever",
    )
    browser = await zd_util.create_from_undetected_chromedriver(driver)
    assert started[0].host == "127.0.0.1"
    assert started[0].port == 9333
    assert browser._process_pid == 4242
    assert stopped == [True]
    assert driver.browser_pid == -1


async def test_local_launch_without_executable_raises_clear_error(
    no_local_browser: None, tmp_path: Any
) -> None:
    # a host+port config later switched to a local launch must fail with the
    # usual FileNotFoundError, not a TypeError from pathlib.Path(None)
    try:
        config = zd.Config(host="127.0.0.1", port=9222, user_data_dir=tmp_path)
    except FileNotFoundError:
        pytest.skip("Config(host, port) itself needs a local browser (unfixed code)")
    config.host = None
    config.port = None
    with pytest.raises(FileNotFoundError):
        await asyncio.wait_for(zd.Browser.create(config), 10)
