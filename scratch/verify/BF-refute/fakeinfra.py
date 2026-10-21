import asyncio, ssl, os
HERE = os.path.dirname(os.path.abspath(__file__))
EV = []  # event log
def log(*a):
    EV.append(" ".join(str(x) for x in a))

def server_ctx():
    c = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    c.load_cert_chain(os.path.join(HERE, "cert.pem"), os.path.join(HERE, "key.pem"))
    return c

def insecure_client_ctx():
    c = ssl.create_default_context(); c.check_hostname = False; c.verify_mode = ssl.CERT_NONE
    return c

async def start_origin(tls=True):
    """HTTP/1.1 keep-alive origin; never closes on its own. logs EOF from client."""
    n = [0]
    async def h(r, w):
        n[0] += 1; cid = n[0]; log("origin: conn", cid, "open")
        try:
            while True:
                try:
                    head = await r.readuntil(b"\r\n\r\n")
                except asyncio.IncompleteReadError as e:
                    log("origin: conn", cid, "EOF from client (partial=%d)" % len(e.partial)); break
                body = b"<html><body><p>hello</p></body></html>"
                w.write(b"HTTP/1.1 200 OK\r\nContent-Type: text/html\r\nContent-Length: %d\r\nConnection: keep-alive\r\n\r\n" % len(body) + body)
                await w.drain()
        except Exception as e:
            log("origin: conn", cid, "error", repr(e))
        finally:
            log("origin: conn", cid, "closing"); w.close()
    s = await asyncio.start_server(h, "127.0.0.1", 0, ssl=server_ctx() if tls else None)
    return s, s.sockets[0].getsockname()[1]

async def start_connect_proxy(origin_port, tls=True):
    """HTTP CONNECT proxy (TLS or plain) that tunnels every CONNECT to the local origin.
    forwards EOF both ways (write_eof when possible, else close)."""
    n = [0]
    async def relay(r, w, name):
        try:
            while d := await r.read(65536):
                w.write(d); await w.drain()
            log("proxy:", name, "EOF")
        except Exception as e:
            log("proxy:", name, "error", repr(e))
        finally:
            if w.can_write_eof():
                try: w.write_eof()
                except Exception: w.close()
            else:
                w.close()
    async def h(r, w):
        n[0] += 1; cid = n[0]
        try:
            head = await r.readuntil(b"\r\n\r\n")
        except Exception as e:
            log("proxy: conn", cid, "no head", repr(e)); w.close(); return
        line = head.split(b"\r\n")[0]
        log("proxy: conn", cid, line.decode())
        orr, ow = await asyncio.open_connection("127.0.0.1", origin_port)
        w.write(b"HTTP/1.1 200 OK\r\n\r\n"); await w.drain()
        await asyncio.gather(relay(r, ow, f"conn{cid} client->origin"), relay(orr, w, f"conn{cid} origin->client"))
        w.close(); ow.close()
        log("proxy: conn", cid, "done")
    s = await asyncio.start_server(h, "127.0.0.1", 0, ssl=server_ctx() if tls else None)
    return s, s.sockets[0].getsockname()[1]
