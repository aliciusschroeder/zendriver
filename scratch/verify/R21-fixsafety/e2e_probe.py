"""End-to-end probe: does zendriver.start() fail when http_proxy points at a
proxy that cannot reach loopback, and no no_proxy is set?"""

import asyncio
import os
import sys
import time

import zendriver

print("zendriver imported from", zendriver.__file__, "python", sys.version.split()[0])

seen: list[bytes] = []


async def handle_proxy(reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
    try:
        line = await reader.readline()
        seen.append(line.strip())
        # drain headers
        while True:
            h = await reader.readline()
            if h in (b"\r\n", b"\n", b""):
                break
        body = b"proxy cannot reach loopback"
        writer.write(
            b"HTTP/1.1 502 Bad Gateway\r\nContent-Length: %d\r\nConnection: close\r\n\r\n%s"
            % (len(body), body)
        )
        await writer.drain()
    finally:
        writer.close()


async def main() -> None:
    server = await asyncio.start_server(handle_proxy, "127.0.0.1", 0)
    pport = server.sockets[0].getsockname()[1]
    for k in ("no_proxy", "NO_PROXY", "HTTP_PROXY", "HTTPS_PROXY", "https_proxy", "ALL_PROXY", "all_proxy"):
        os.environ.pop(k, None)
    os.environ["http_proxy"] = f"http://127.0.0.1:{pport}"
    print("http_proxy =", os.environ["http_proxy"])
    t0 = time.monotonic()
    browser = None
    try:
        browser = await asyncio.wait_for(
            zendriver.start(headless=True, browser_connection_max_tries=3), 60
        )
        print(f"start OK after {time.monotonic() - t0:.1f}s; version:", browser.info.Browser)
    except Exception as e:  # noqa
        print(f"start FAILED after {time.monotonic() - t0:.1f}s: {type(e).__name__}: {str(e).strip().splitlines()[:3]}")
    finally:
        if browser is not None:
            await browser.stop()
        server.close()
        await server.wait_closed()
    print("requests seen by proxy:", len(seen))
    for s in seen:
        print("  ", s)


asyncio.run(main())
