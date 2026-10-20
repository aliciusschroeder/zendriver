import asyncio, sys
import zendriver.core.proxy as proxy
print(proxy.__file__, sys.version.split()[0], "TimeoutError is OSError subclass:", issubclass(asyncio.TimeoutError, OSError))
async def main():
    async def silent(r, w):
        await r.read()
    server = await asyncio.start_server(silent, "127.0.0.1", 0)
    port = server.sockets[0].getsockname()[1]
    proxy.TIMEOUT = 0.3
    up = proxy.UpstreamProxy.from_url(f"http://u:p@127.0.0.1:{port}")
    try:
        await asyncio.wait_for(up.open_tunnel("example.com", 443), 5)
    except proxy.ProxyError as e:
        print("ProxyError:", e)
    server.close()
asyncio.run(main())
