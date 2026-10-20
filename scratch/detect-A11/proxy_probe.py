import asyncio, ssl, logging, os, sys
from zendriver.core import proxy as P

HERE = os.path.dirname(os.path.abspath(__file__))
logging.basicConfig(level=logging.WARNING, format="LOG %(levelname)s %(name)s: %(message)s")

async def origin_handler(r, w):
    # behaves like a typical server: closes its side when the peer sends EOF
    try:
        while await r.read(65536):
            pass
    finally:
        w.close()

async def fake_proxy_handler(r, w):
    # minimal CONNECT proxy (no auth check) which propagates half-close like real proxies
    head = await r.readuntil(b"\r\n\r\n")
    target = head.split(b" ")[1].decode()
    host, port = target.rsplit(":", 1)
    ur, uw = await asyncio.open_connection(host, int(port))
    w.write(b"HTTP/1.1 200 Connection Established\r\n\r\n")
    try:
        await P.pipe(r, w, ur, uw)
    finally:
        w.close()

async def tunnel_case(tls: bool):
    origin = await asyncio.start_server(origin_handler, "127.0.0.1", 0)
    oport = origin.sockets[0].getsockname()[1]
    sctx = None
    if tls:
        sctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        sctx.load_cert_chain(os.path.join(HERE, "cert.pem"), os.path.join(HERE, "key.pem"))
    prox = await asyncio.start_server(fake_proxy_handler, "127.0.0.1", 0, ssl=sctx)
    pport = prox.sockets[0].getsockname()[1]
    cctx = ssl.create_default_context(); cctx.check_hostname = False; cctx.verify_mode = ssl.CERT_NONE
    up = P.UpstreamProxy.from_url(f"{'https' if tls else 'http'}://u:p@127.0.0.1:{pport}", cctx)
    fw = P.ProxyForwarder(up); await fw.start()
    fport = int(fw.proxy_server.rsplit(":", 1)[1])
    r, w = await asyncio.open_connection("127.0.0.1", fport)
    w.write(f"CONNECT 127.0.0.1:{oport} HTTP/1.1\r\nHost: 127.0.0.1:{oport}\r\n\r\n".encode())
    print(" resp:", (await asyncio.wait_for(r.readuntil(b"\r\n\r\n"), 5))[:40])
    await asyncio.sleep(0.2)
    w.close()  # the browser closes its socket (FIN)
    await asyncio.sleep(2)
    print(f" tls={tls}: forwarder client tasks still alive 2s after client closed: {len(fw._client_tasks)}")
    t0 = asyncio.get_running_loop().time()
    await asyncio.wait_for(fw.close(), 10)
    prox.close(); origin.close()

async def timeout_msg_case():
    async def silent(r, w):
        await asyncio.sleep(5); w.close()
    prox = await asyncio.start_server(silent, "127.0.0.1", 0)
    pport = prox.sockets[0].getsockname()[1]
    P.TIMEOUT = 0.5
    up = P.UpstreamProxy.from_url(f"http://u:p@127.0.0.1:{pport}")
    try:
        await up.open_tunnel("example.com", 443)
    except P.ProxyError as e:
        print(" handshake timeout ->", repr(str(e)))
    P.TIMEOUT = 30
    prox.close()

async def idna_case():
    async def socks(r, w):
        await r.readexactly(4); w.write(b"\x05\x00")
        await asyncio.sleep(5)
    prox = await asyncio.start_server(socks, "127.0.0.1", 0)
    pport = prox.sockets[0].getsockname()[1]
    fw = P.ProxyForwarder(P.UpstreamProxy.from_url(f"socks5://u:p@127.0.0.1:{pport}")); await fw.start()
    fport = int(fw.proxy_server.rsplit(":", 1)[1])
    r, w = await asyncio.open_connection("127.0.0.1", fport)
    host = "a" * 64 + ".example.com"
    w.write(f"CONNECT {host}:443 HTTP/1.1\r\nHost: {host}:443\r\n\r\n".encode())
    print(" long-label CONNECT response:", await asyncio.wait_for(r.read(), 5))
    await fw.close(); prox.close()

async def main():
    print("== tunnel half-close, plain upstream"); await tunnel_case(False)
    print("== tunnel half-close, TLS upstream"); await tunnel_case(True)
    print("== handshake timeout message"); await timeout_msg_case()
    print("== long label via socks"); await idna_case()

asyncio.run(main())
