"""Regression tests for Q9: Browser/Connection __aexit__ must not rebuild the exception."""

import asyncio
import json
import os
import subprocess
import sys
import textwrap
from typing import Any, AsyncIterator, Callable

import pytest
import websockets
import websockets.asyncio.server
import websockets.exceptions

import zendriver as zd
from zendriver import cdp
from zendriver.core.connection import Connection, ProtocolException

print("zendriver imported from:", zd.__file__)


def _make_json_error() -> BaseException:
    try:
        json.loads("{bad")
    except json.JSONDecodeError as e:
        return e
    raise AssertionError("unreachable")


async def _make_group_error() -> BaseException:
    async def boom() -> None:
        raise ValueError("inner")

    try:
        async with asyncio.TaskGroup() as tg:
            tg.create_task(boom())
    except BaseExceptionGroup as e:
        return e
    raise AssertionError("unreachable")


def _make_unicode_error() -> BaseException:
    try:
        b"\xff".decode("utf-8")
    except UnicodeDecodeError as e:
        return e
    raise AssertionError("unreachable")


ERROR_FACTORIES: dict[str, Callable[[], Any]] = {
    "json": _make_json_error,
    "unicode": _make_unicode_error,
    "ws_closed": lambda: websockets.exceptions.ConnectionClosedError(None, None),
    "protocol": lambda: ProtocolException({"code": -32000, "message": "m"}),
    "keyerror": lambda: KeyError("k"),
}


async def _build_error(name: str) -> BaseException:
    if name == "group":
        return await _make_group_error()
    return ERROR_FACTORIES[name]()


ALL_ERRORS = [*ERROR_FACTORIES, "group"]


@pytest.fixture
async def fake_cdp_url() -> AsyncIterator[str]:
    async def handler(ws: websockets.asyncio.server.ServerConnection) -> None:
        try:
            async for raw in ws:
                msg = json.loads(raw)
                if msg["method"] == "DOM.resolveNode":
                    reply = {
                        "id": msg["id"],
                        "error": {
                            "code": -32000,
                            "message": "No node with given id found",
                        },
                    }
                elif msg["method"] == "Target.getTargets":
                    reply = {"id": msg["id"], "result": {"targetInfos": []}}
                else:
                    reply = {"id": msg["id"], "result": {}}
                await ws.send(json.dumps(reply))
        except websockets.exceptions.ConnectionClosed:
            pass

    async with websockets.asyncio.server.serve(handler, "127.0.0.1", 0) as server:
        port = server.sockets[0].getsockname()[1]
        yield f"ws://127.0.0.1:{port}/devtools/browser/fake"


@pytest.mark.parametrize("name", ALL_ERRORS)
async def test_browser_aexit_propagates_original_exception(name: str) -> None:
    browser = zd.Browser(zd.Config(headless=True))
    original = await _build_error(name)
    with pytest.raises(BaseException) as excinfo:
        async with browser:
            raise original
    assert excinfo.value is original, repr(excinfo.value)


@pytest.mark.parametrize("name", ALL_ERRORS)
async def test_connection_aexit_propagates_original_exception(
    name: str, fake_cdp_url: str
) -> None:
    conn = Connection(fake_cdp_url)
    original = await _build_error(name)
    with pytest.raises(BaseException) as excinfo:
        async with conn:
            await conn.send(cdp.target.get_targets())
            raise original
    assert excinfo.value is original, repr(excinfo.value)
    assert conn.websocket is None  # aclose() still ran


async def test_connection_aexit_keeps_protocol_exception_code(
    fake_cdp_url: str,
) -> None:
    conn = Connection(fake_cdp_url)
    with pytest.raises(ProtocolException) as excinfo:
        async with conn:
            await conn.send(cdp.dom.resolve_node(node_id=cdp.dom.NodeId(999999)))
    assert excinfo.value.code == -32000
    assert excinfo.value.message is not None
    assert "No node with given id found" in excinfo.value.message


async def test_aexit_passes_through_when_no_exception(fake_cdp_url: str) -> None:
    browser = zd.Browser(zd.Config(headless=True))
    async with browser as b:
        assert b is browser
    conn = Connection(fake_cdp_url)
    async with conn as c:
        assert c is conn
        await conn.send(cdp.target.get_targets())
    assert conn.websocket is None


async def test_cancellation_inside_aexit_block_is_timeout() -> None:
    browser = zd.Browser(zd.Config(headless=True))
    with pytest.raises(TimeoutError):
        async with asyncio.timeout(0.05):
            async with browser:
                await asyncio.sleep(10)


def test_sys_exit_status_preserved_through_browser_aexit() -> None:
    script = textwrap.dedent(
        """
        import asyncio, sys
        import zendriver as zd

        async def main():
            async with zd.Browser(zd.Config(headless=True)):
                sys.exit(3)

        asyncio.run(main())
        """
    )
    proc = subprocess.run(
        [sys.executable, "-c", script],
        env=os.environ.copy(),
        capture_output=True,
        text=True,
        timeout=60,
        cwd=os.path.dirname(os.path.abspath(__file__)),
    )
    assert proc.returncode == 3, (proc.returncode, proc.stderr[-500:])
