import asyncio, importlib.util, os, ssl, sys
spec = importlib.util.spec_from_file_location("proxymod", sys.argv[1]); m = importlib.util.module_from_spec(spec); sys.modules["proxymod"] = m; spec.loader.exec_module(m)
CERTS = sys.argv[2]
async def main():
    sctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER); sctx.load_cert_chain(f"{CERTS}/cert.pem", f"{CERTS}/key.pem")
    cctx = ssl.create_default_context(cafile=f"{CERTS}/cert.pem")
    closed = asyncio.Event()
    async def h(r, w):
        try:
            await r.readuntil(b"\r\n\r\n"); w.write(b"HTTP/1.1 200 OK\r\n\r\n")
            while d := await r.read(1024): w.write(d); await w.drain()
        except Exception as e: pass
        finally: closed.set(); w.close()
    srv = await asyncio.start_server(h, "127.0.0.1", 0, ssl=sctx); port = srv.sockets[0].getsockname()[1]
    fw = m.ProxyForwarder(m.UpstreamProxy("https", "127.0.0.1", port, "u", "p", cctx)); await fw.start()
    host, fport = fw.proxy_server.rsplit("/",1)[1].split(":")
    r, w = await asyncio.open_connection(host, int(fport))
    w.write(b"CONNECT x:443 HTTP/1.1\r\n\r\n"); await r.readuntil(b"\r\n\r\n"); w.write(b"ping"); assert await r.readexactly(4) == b"ping"
    w.close(); t0 = asyncio.get_running_loop().time()
    for _ in range(50):
        if closed.is_set() and not fw._client_tasks: break
        await asyncio.sleep(0.1)
    print(sys.version_info[:2], os.path.basename(os.path.dirname(os.path.dirname(os.path.dirname(sys.argv[1])))), "upstream closed:", closed.is_set(), "tasks left:", len(fw._client_tasks), "after %.1fs" % (asyncio.get_running_loop().time()-t0))
    await fw.close(); srv.close()
asyncio.run(main())
