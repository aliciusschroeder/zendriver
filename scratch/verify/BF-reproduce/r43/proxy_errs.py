import asyncio, sys, logging, io
import zendriver.core.proxy as P
print("proxy module from", P.__file__, "python", sys.version.split()[0])
buf = io.StringIO()
h = logging.StreamHandler(buf); h.setFormatter(logging.Formatter("LOG %(levelname)s %(name)s: %(message)s"))
logging.getLogger().addHandler(h); logging.getLogger().setLevel(logging.WARNING)

async def socks_server(reader, writer):
    try:
        await reader.readexactly(4)              # greeting 05 02 00 02
        writer.write(b"\x05\x02"); await writer.drain()
        ver, ulen = await reader.readexactly(2)
        await reader.readexactly(ulen); (plen,) = await reader.readexactly(1); await reader.readexactly(plen)
        writer.write(b"\x01\x00"); await writer.drain()
        req = await reader.read(1024)            # would be the CONNECT request
        writer.write(b"\x05\x00\x00\x01" + b"\x7f\x00\x00\x01" + b"\x00\x50"); await writer.drain()
        await reader.read()
    except Exception:
        pass
    writer.close()

async def silent_server(reader, writer):
    await asyncio.sleep(30)
    writer.close()

async def ask(fport, raw):
    r, w = await asyncio.open_connection("127.0.0.1", fport)
    w.write(raw); await w.drain()
    try:
        resp = await asyncio.wait_for(r.read(200), 10)
    except asyncio.TimeoutError:
        resp = "<no reply within 10s>"
    w.close()
    return resp

async def main():
    ss = await asyncio.start_server(socks_server, "127.0.0.1", 0)
    sport = ss.sockets[0].getsockname()[1]
    fw = P.ProxyForwarder(P.UpstreamProxy.from_url(f"socks5://u:p@127.0.0.1:{sport}"))
    await fw.start(); fport = int(fw.proxy_server.rsplit(":", 1)[1])
    cases = {
        "long-label CONNECT": f"CONNECT {'a'*64}.example.com:443 HTTP/1.1\r\n\r\n".encode(),
        "empty-label CONNECT": b"CONNECT a..b.com:443 HTTP/1.1\r\n\r\n",
        "GET bad port (socks)": b"GET http://example.com:99999/ HTTP/1.1\r\nHost: example.com\r\n\r\n",
        "GET bad ipv6 url": b"GET http://[bad/ HTTP/1.1\r\n\r\n",
        "control: bad CONNECT target": b"CONNECT nohostport HTTP/1.1\r\n\r\n",
    }
    for name, raw in cases.items():
        buf.truncate(0); buf.seek(0)
        resp = await ask(fport, raw)
        await asyncio.sleep(0.2)
        logs = [l for l in buf.getvalue().splitlines() if l.startswith("LOG") or "Error" in l]
        print(f"{name}: response={resp!r}")
        for l in logs[:1] + [l for l in logs if "Error:" in l][-1:]:
            print("    ", l[:200])
    await fw.close(); ss.close()

    # A11.9: proxy accepts TCP but never answers the handshake
    P.TIMEOUT = 0.5
    sil = await asyncio.start_server(silent_server, "127.0.0.1", 0)
    port = sil.sockets[0].getsockname()[1]
    for scheme in ("http", "socks5"):
        up = P.UpstreamProxy.from_url(f"{scheme}://u:p@127.0.0.1:{port}")
        try:
            await asyncio.wait_for(up.open_tunnel("example.com", 443), 10)
        except P.ProxyError as e:
            print(f"handshake timeout ({scheme}) -> ProxyError({str(e)!r}) cause={type(e.__cause__).__name__}; "
                  f"TimeoutError is OSError subclass: {issubclass(asyncio.TimeoutError, OSError)}")
    sil.close()

asyncio.run(asyncio.wait_for(main(), 100))
