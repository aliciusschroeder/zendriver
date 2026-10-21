import asyncio
import os
import ssl

import pytest

import zendriver
from zendriver.core import proxy
from zendriver.core.proxy import ProxyError, ProxyForwarder, UpstreamProxy

CERTS = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "certs")


def test_print_origin() -> None:
    print("zendriver imported from", zendriver.__file__)


async def _serve(handler, ssl_ctx=None):
    server = await asyncio.start_server(handler, "127.0.0.1", 0, ssl=ssl_ctx)
    return server, server.sockets[0].getsockname()[1]


@pytest.mark.parametrize("scheme", ["http", "socks5"])
async def test_handshake_timeout_is_reported_as_timeout(monkeypatch, scheme) -> None:
    monkeypatch.setattr(proxy, "TIMEOUT", 0.3)
    held = []

    async def silent(reader, writer):
        held.append(writer)
        await asyncio.sleep(30)

    server, port = await _serve(silent)
    try:
        upstream = UpstreamProxy(scheme, "127.0.0.1", port, "u", "p")
        with pytest.raises(ProxyError) as ei:
            await asyncio.wait_for(upstream.open_tunnel("example.com", 443), 10)
        assert str(ei.value) == "timed out waiting for the proxy"
    finally:
        for w in held:
            w.close()
        server.close()


async def _socks5_server():
    async def handler(reader, writer):
        try:
            await reader.readexactly(4)
            writer.write(b"\x05\x02")
            ver, ulen = await reader.readexactly(2)
            await reader.readexactly(ulen)
            (plen,) = await reader.readexactly(1)
            await reader.readexactly(plen)
            writer.write(b"\x01\x00")
            await reader.read(1024)  # the connect request, never answered
        except Exception:
            pass
        finally:
            writer.close()

    return await _serve(handler)


@pytest.mark.parametrize(
    "request_head",
    [
        b"CONNECT " + b"a" * 64 + b".example.com:443 HTTP/1.1\r\n\r\n",
        b"CONNECT a..b.com:443 HTTP/1.1\r\n\r\n",
        b"CONNECT " + (b"a" * 60 + b".") * 5 + b"com:443 HTTP/1.1\r\n\r\n",
        b"CONNECT [::1:443 HTTP/1.1\r\n\r\n",
        b"GET http://example.com:99999/ HTTP/1.1\r\nHost: example.com\r\n\r\n",
        b"GET http://[::1/ HTTP/1.1\r\n\r\n",
    ],
    ids=["long-label", "empty-label", "over-255", "bad-ipv6-connect", "bad-port", "bad-ipv6-get"],
)
async def test_bad_targets_get_an_http_error(request_head: bytes) -> None:
    loop = asyncio.get_running_loop()
    unhandled = []
    loop.set_exception_handler(lambda loop, ctx: unhandled.append(ctx))
    server, port = await _socks5_server()
    forwarder = ProxyForwarder(UpstreamProxy("socks5", "127.0.0.1", port, "u", "p"))
    await forwarder.start()
    try:
        host, fport = forwarder.proxy_server.rsplit("/", 1)[1].split(":")
        reader, writer = await asyncio.open_connection(host, int(fport))
        writer.write(request_head)
        response = await asyncio.wait_for(reader.read(1024), 10)
        writer.close()
        await asyncio.sleep(0.1)
        assert response.startswith(b"HTTP/1.1 400 ") or response.startswith(b"HTTP/1.1 502 "), response
        assert not unhandled, unhandled
    finally:
        loop.set_exception_handler(None)
        await forwarder.close()
        server.close()


@pytest.mark.parametrize("tls", [False, True], ids=["http-upstream", "https-upstream"])
async def test_tunnel_is_torn_down_when_client_closes(tls: bool) -> None:
    server_ctx = None
    client_ctx = None
    if tls:
        server_ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        server_ctx.load_cert_chain(os.path.join(CERTS, "cert.pem"), os.path.join(CERTS, "key.pem"))
        client_ctx = ssl.create_default_context(cafile=os.path.join(CERTS, "cert.pem"))
    upstream_closed = asyncio.Event()

    async def connect_proxy(reader, writer):
        # CONNECT proxy whose "origin" echoes until the client side goes away
        try:
            await reader.readuntil(b"\r\n\r\n")
            writer.write(b"HTTP/1.1 200 Connection Established\r\n\r\n")
            while data := await reader.read(1024):
                writer.write(data)
                await writer.drain()
        except Exception:
            pass
        finally:
            upstream_closed.set()
            writer.close()

    server, port = await _serve(connect_proxy, server_ctx)
    forwarder = ProxyForwarder(
        UpstreamProxy("https" if tls else "http", "127.0.0.1", port, "u", "p", client_ctx)
    )
    await forwarder.start()
    try:
        host, fport = forwarder.proxy_server.rsplit("/", 1)[1].split(":")
        reader, writer = await asyncio.open_connection(host, int(fport))
        writer.write(b"CONNECT example.com:443 HTTP/1.1\r\n\r\n")
        assert (await asyncio.wait_for(reader.readuntil(b"\r\n\r\n"), 10)).startswith(b"HTTP/1.1 200")
        writer.write(b"ping")
        assert await asyncio.wait_for(reader.readexactly(4), 10) == b"ping"
        assert len(forwarder._client_tasks) == 1
        writer.close()  # chrome drops the connection
        await asyncio.wait_for(writer.wait_closed(), 10)
        for _ in range(30):
            if not forwarder._client_tasks and upstream_closed.is_set():
                break
            await asyncio.sleep(0.1)
        assert upstream_closed.is_set(), "upstream tunnel still open 3s after the client closed"
        assert not forwarder._client_tasks, "forwarder task still alive 3s after the client closed"
    finally:
        await forwarder.close()
        server.close()
