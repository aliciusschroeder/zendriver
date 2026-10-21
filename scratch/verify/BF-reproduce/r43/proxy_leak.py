import asyncio, ssl, sys, logging
import zendriver.core.proxy as P
print("proxy module from", P.__file__, "python", sys.version.split()[0])
HERE = sys.path[0]

async def fake_proxy_handler(reader, writer, state):
    # CONNECT proxy that acts as the origin after the tunnel is up:
    # the origin waits for the client's EOF, then closes (typical server behaviour).
    head = await reader.readuntil(b"\r\n\r\n")
    state["connect"] = head.split(b"\r\n")[0]
    writer.write(b"HTTP/1.1 200 Connection Established\r\n\r\n")
    await writer.drain()
    try:
        while await reader.read(65536):
            pass
        state["origin_saw_eof"] = True
    except Exception as e:
        state["origin_err"] = repr(e)
    writer.close()

async def run(tls: bool, wait: float):
    state = {"origin_saw_eof": False}
    sctx = None
    if tls:
        sctx = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
        sctx.load_cert_chain(f"{HERE}/cert.pem", f"{HERE}/key.pem")
    srv = await asyncio.start_server(lambda r, w: fake_proxy_handler(r, w, state), "127.0.0.1", 0, ssl=sctx)
    port = srv.sockets[0].getsockname()[1]
    cctx = ssl.create_default_context(); cctx.check_hostname = False; cctx.verify_mode = ssl.CERT_NONE
    scheme = "https" if tls else "http"
    up = P.UpstreamProxy.from_url(f"{scheme}://u:p@127.0.0.1:{port}", cctx)
    fw = P.ProxyForwarder(up)
    await fw.start()
    fport = int(fw.proxy_server.rsplit(":", 1)[1])
    r, w = await asyncio.open_connection("127.0.0.1", fport)
    w.write(b"CONNECT example.com:443 HTTP/1.1\r\nHost: example.com:443\r\n\r\n")
    print(f"  tls={tls}: client got", (await r.readuntil(b"\r\n\r\n")).split(b"\r\n")[0])
    w.write(b"hello")
    await w.drain()
    await asyncio.sleep(0.2)
    w.close()                 # client (Chrome) closes the tunnelled connection
    await w.wait_closed()
    await asyncio.sleep(wait)
    alive = [t for t in fw._client_tasks if not t.done()]
    print(f"  tls={tls}: forwarder client tasks alive {wait}s after client closed: {len(alive)}; origin_saw_eof={state['origin_saw_eof']}")
    for t in alive:
        print("  stuck task stack:")
        t.print_stack(file=sys.stdout)
    await asyncio.wait_for(fw.close(), 10)
    srv.close()
    await srv.wait_closed()

async def main():
    await run(False, 2)
    await run(True, 2)
    await run(True, 10)

asyncio.run(asyncio.wait_for(main(), 90))
