"""Companion test for R21: on websockets >= 15 the CDP websocket must not go
through the proxy of the environment either."""

import asyncio
import urllib.request

import pytest
import websockets
import websockets.asyncio.server

import zendriver
from zendriver.core.connection import Connection

print("zendriver imported from", zendriver.__file__, "websockets", websockets.__version__)


@pytest.mark.parametrize("var", ["http_proxy", "https_proxy"])
async def test_connection_does_not_use_env_proxy(
    monkeypatch: pytest.MonkeyPatch, var: str
) -> None:
    seen: list[bytes] = []

    async def proxy(reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
        seen.append(await reader.readline())
        writer.write(b"HTTP/1.1 502 Bad Gateway\r\nContent-Length: 0\r\n\r\n")
        await writer.drain()
        writer.close()

    async def peer(ws: websockets.asyncio.server.ServerConnection) -> None:
        await ws.wait_closed()

    proxy_server = await asyncio.start_server(proxy, "127.0.0.1", 0)
    async with websockets.asyncio.server.serve(peer, "127.0.0.1", 0) as peer_server:
        for name in ("no_proxy", "NO_PROXY", "http_proxy", "HTTP_PROXY",
                     "https_proxy", "HTTPS_PROXY", "all_proxy", "ALL_PROXY"):
            monkeypatch.delenv(name, raising=False)
        monkeypatch.setenv(var, "http://127.0.0.1:%d" % proxy_server.sockets[0].getsockname()[1])
        monkeypatch.setattr(urllib.request, "_opener", None)
        port = peer_server.sockets[0].getsockname()[1]
        conn = Connection(f"ws://127.0.0.1:{port}/devtools/browser/x")
        try:
            await asyncio.wait_for(conn.aopen(), 10)
            assert conn.websocket is not None
        finally:
            await conn.aclose()
    proxy_server.close()
    await proxy_server.wait_closed()
    assert seen == []
