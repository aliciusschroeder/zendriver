"""SEED-X3: does UpstreamProxy.open_tunnel swallow CancelledError?
Fake upstream that accepts TCP and never answers CONNECT / SOCKS greeting."""
import asyncio
import sys
import time

import zendriver
from zendriver.core.proxy import UpstreamProxy

print("zendriver from", zendriver.__file__, "python", sys.version.split()[0])

writers_seen = []


async def silent(reader, writer):
    writers_seen.append(writer)
    try:
        await reader.read()  # wait for client close
    finally:
        writer.close()


async def main():
    server = await asyncio.start_server(silent, "127.0.0.1", 0)
    port = server.sockets[0].getsockname()[1]
    for scheme in ("http", "socks5"):
        up = UpstreamProxy.from_url(f"{scheme}://u:p@127.0.0.1:{port}")
        # task.cancel()
        t0 = time.monotonic()
        task = asyncio.create_task(up.open_tunnel("example.com", 443))
        await asyncio.sleep(0.5)
        task.cancel()
        done, _ = await asyncio.wait({task}, timeout=5)
        try:
            r = task.result()
            print(f"[{scheme} cancel] returned {r!r} -> SWALLOWED")
        except BaseException as e:
            print(f"[{scheme} cancel] {type(e).__name__} after {time.monotonic()-t0:.2f}s")
        # outer wait_for
        t0 = time.monotonic()
        try:
            await asyncio.wait_for(
                asyncio.wait_for(up.open_tunnel("example.com", 443), 0.5), 5
            )
        except BaseException as e:
            print(f"[{scheme} wait_for 0.5] {type(e).__name__} after {time.monotonic()-t0:.2f}s")
    await asyncio.sleep(0.2)
    # client side writers closed by open_tunnel -> server reader sees EOF
    print("server-side connections:", len(writers_seen))
    server.close()
    await server.wait_closed()


asyncio.run(asyncio.wait_for(main(), 60))
