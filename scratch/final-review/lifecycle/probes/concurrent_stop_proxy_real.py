"""public API: a context with an authenticated proxy carries a request whose upstream
tunnel stays open; then two stop() calls run at once (e.g. a finally block plus a
signal handler, or gather over a list that holds the browser twice)."""
import asyncio, os, shutil, sys, logging
import zendriver as zd
logging.basicConfig(level=logging.ERROR)
CHROME = shutil.which("chromium")

async def upstream_handler(reader, writer):
    await reader.readuntil(b"\r\n\r\n")
    writer.write(b"HTTP/1.1 200 Connection Established\r\n\r\n")
    await writer.drain()
    try:
        while await reader.read(65536):   # hold the tunnel open, never answer TLS
            pass
        await asyncio.sleep(3600)        # ignore EOF too
    except Exception:
        pass

async def main():
    print(sys.version.split()[0], zd.__file__)
    up = await asyncio.start_server(upstream_handler, "127.0.0.1", 0)
    upport = up.sockets[0].getsockname()[1]
    results = []
    for i in range(3):
        b = await zd.start(headless=True, sandbox=False, browser_executable_path=CHROME)
        ctx = await b.create_context(proxy_server=f"http://user:pass@127.0.0.1:{upport}")
        nav = asyncio.ensure_future(ctx.get("https://example.test/"))
        await asyncio.sleep(1.0)
        fw = b._proxy_forwarders[0]
        n_clients = len(fw._client_tasks)
        r = await asyncio.wait_for(asyncio.gather(b.stop(), b.stop(), return_exceptions=True), 60)
        nav.cancel(); await asyncio.gather(nav, return_exceptions=True)
        print(f"run {i}: forwarder clients before stop={n_clients} results={[repr(x) for x in r]} profile_left={os.path.exists(b.config.user_data_dir)} process={b._process}")
    up.close()

asyncio.run(main())
