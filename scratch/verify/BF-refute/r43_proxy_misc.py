import asyncio, sys, logging
import zendriver
from zendriver.core import proxy as P
print("zendriver from", zendriver.__file__, sys.version.split()[0])
print("issubclass(asyncio.TimeoutError, OSError):", issubclass(asyncio.TimeoutError, OSError))
logs = []
class H(logging.Handler):
    def emit(self, r): logs.append((r.name, r.levelname, r.getMessage().splitlines()[0], r.exc_info[0].__name__ if r.exc_info else None))
logging.getLogger().addHandler(H()); logging.getLogger().setLevel(logging.DEBUG)

async def silent_server():
    conns = []
    async def h(r, w): conns.append(w); await asyncio.sleep(3600)
    s = await asyncio.start_server(h, "127.0.0.1", 0)
    return s, s.sockets[0].getsockname()[1], conns

async def socks_server():
    # minimal socks5: accept user/pass, reply success, then echo
    async def h(r, w):
        try:
            await r.readexactly(4); w.write(b"\x05\x02")
            v, ul = await r.readexactly(2); await r.readexactly(ul); (pl,) = await r.readexactly(1); await r.readexactly(pl)
            w.write(b"\x01\x00")
            hdr = await r.readexactly(4); atyp = hdr[3]
            if atyp == 3: (l,) = await r.readexactly(1); await r.readexactly(l + 2)
            elif atyp == 1: await r.readexactly(6)
            else: await r.readexactly(18)
            w.write(b"\x05\x00\x00\x01" + bytes(6))
            while d := await r.read(65536): w.write(d)
        except Exception as e:
            pass
        finally: w.close()
    s = await asyncio.start_server(h, "127.0.0.1", 0)
    return s, s.sockets[0].getsockname()[1]

async def main():
    # A11.9
    P.TIMEOUT = 0.5
    s, port, conns = await silent_server()
    for scheme in ("http", "socks5"):
        up = P.UpstreamProxy.from_url(f"{scheme}://u:p@127.0.0.1:{port}")
        try:
            await asyncio.wait_for(up.open_tunnel("example.com", 443), 10)
        except P.ProxyError as e:
            print(f"A11.9 {scheme} handshake timeout -> ProxyError({str(e)!r})")
    s.close()
    P.TIMEOUT = 30
    # A11.7 via forwarder with socks5 upstream
    ss, sport = await socks_server()
    fw = P.ProxyForwarder(P.UpstreamProxy.from_url(f"socks5://u:p@127.0.0.1:{sport}"))
    await fw.start()
    fport = int(fw.proxy_server.rsplit(":", 1)[1])
    async def req(raw):
        r, w = await asyncio.open_connection("127.0.0.1", fport)
        w.write(raw); await w.drain()
        try: resp = await asyncio.wait_for(r.read(200), 5)
        except Exception as e: resp = repr(e)
        w.close(); return resp
    print("A11.7 control normal CONNECT:", await req(b"CONNECT example.com:443 HTTP/1.1\r\n\r\n"))
    print("A11.7 control bad authority:", await req(b"CONNECT example.com HTTP/1.1\r\n\r\n"))
    for raw in [("CONNECT " + "a"*64 + ".example.com:443 HTTP/1.1\r\n\r\n").encode(),
                b"CONNECT a..b.com:443 HTTP/1.1\r\n\r\n",
                b"GET http://a..b.com/ HTTP/1.1\r\nHost: a..b.com\r\n\r\n",
                b"GET http://example.com:99999/ HTTP/1.1\r\n\r\n",
                b"GET http://[::1/ HTTP/1.1\r\n\r\n",
                b"GET http://example.com:abc/ HTTP/1.1\r\n\r\n"]:
        logs.clear()
        resp = await req(raw)
        await asyncio.sleep(0.2)
        print("A11.7", raw[:40], "->", resp, "| logs:", [l for l in logs if l[1] in ("ERROR","WARNING")])
    await fw.close(); ss.close()
asyncio.run(asyncio.wait_for(main(), 60))
