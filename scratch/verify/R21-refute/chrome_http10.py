import asyncio, sys
import zendriver
async def raw(port, req):
    r, w = await asyncio.open_connection("127.0.0.1", port)
    w.write(req); await w.drain()
    buf = b""
    try:
        while True:
            chunk = await asyncio.wait_for(r.read(4096), 2)
            if not chunk: buf += b"<EOF>"; break
            buf += chunk
    except asyncio.TimeoutError:
        buf += b"<idle 2s>"
    w.close(); return buf[:90] + b"..." + buf[-12:]
async def main():
    b = await asyncio.wait_for(zendriver.start(headless=True), 60)
    try:
        port = b.config.port
        print("HTTP/1.0 :", await raw(port, f"GET /json/version HTTP/1.0\r\nHost: 127.0.0.1:{port}\r\n\r\n".encode()))
        print("HTTP/1.1 close:", await raw(port, f"GET /json/version HTTP/1.1\r\nHost: 127.0.0.1:{port}\r\nConnection: close\r\n\r\n".encode()))
        print("abs-form 1.1 :", await raw(port, f"GET http://127.0.0.1:{port}/json/version HTTP/1.1\r\nHost: 127.0.0.1:{port}\r\nConnection: close\r\n\r\n".encode()))
    finally:
        await b.stop()
asyncio.run(main())
