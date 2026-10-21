import asyncio, sys
sys.path.insert(0, __import__("os").path.dirname(__file__))
import zendriver
from zendriver.core import proxy as P
import fakeinfra as F
print("zendriver from", zendriver.__file__, sys.version.split()[0])
async def run(tls):
    F.EV.clear()
    os_, oport = await F.start_origin(tls=False)  # origin protocol irrelevant here; raw bytes
    ps, pport = await F.start_connect_proxy(oport, tls=tls)
    scheme = "https" if tls else "http"
    fw = P.ProxyForwarder(P.UpstreamProxy.from_url(f"{scheme}://u:p@127.0.0.1:{pport}", F.insecure_client_ctx()))
    await fw.start()
    fport = int(fw.proxy_server.rsplit(":", 1)[1])
    r, w = await asyncio.open_connection("127.0.0.1", fport)
    w.write(b"CONNECT origin.test:443 HTTP/1.1\r\n\r\n"); await w.drain()
    print(f" {scheme}: tunnel reply", await r.readuntil(b"\r\n\r\n"))
    w.write(b"GET / HTTP/1.1\r\nHost: x\r\n\r\n"); await w.drain()
    await asyncio.sleep(0.3)
    print(f" {scheme}: got", len(await r.read(65536)), "bytes")
    w.close(); await w.wait_closed()
    for t in (0.5, 2, 5):
        await asyncio.sleep(t if t == 0.5 else t - prev)
        prev = t
        print(f" {scheme}: {t}s after client close: forwarder client tasks alive = {len(fw._client_tasks)}")
    if fw._client_tasks:
        for task in fw._client_tasks: task.print_stack(limit=3)
    print(f" {scheme}: events", F.EV)
    await asyncio.wait_for(fw.close(), 10)
    print(f" {scheme}: after fw.close(): tasks", len(fw._client_tasks))
    ps.close(); os_.close()
prev = 0.5
async def main():
    global prev
    for tls in (False, True):
        prev = 0.5
        await run(tls)
asyncio.run(asyncio.wait_for(main(), 90))
