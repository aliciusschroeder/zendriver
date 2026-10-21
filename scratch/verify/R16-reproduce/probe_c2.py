"""SEED-C2: aclose() while aopen() is still connecting."""

import asyncio
import sys

sys.path.insert(0, __file__.rsplit("/", 1)[0])

import zendriver
from zendriver.core.connection import Connection

from fake_cdp import FakeCDP

print("zendriver from", zendriver.__file__, "python", sys.version.split()[0])


async def main() -> None:
    peer = await FakeCDP(handshake_delay=0.5).start()
    conn = Connection(peer.url)
    opener = asyncio.create_task(conn.aopen())
    await asyncio.sleep(0.2)
    print("handshake started:", peer.handshakes_started, "websocket is None:", conn.websocket is None)
    await asyncio.wait_for(conn.aclose(), 5)
    print("aclose() returned; websocket is None:", conn.websocket is None, "closed:", conn.closed)
    await asyncio.wait_for(opener, 5)
    await asyncio.sleep(0.2)
    print("after aopen finished: closed:", conn.closed,
          "websocket state:", conn.websocket.state if conn.websocket else None,
          "listener running:", conn.listener.running if conn.listener else None,
          "server-side open connections:", peer.open_connections())
    await conn.aclose()
    await asyncio.sleep(0.1)
    print("after 2nd aclose: server-side open connections:", peer.open_connections())
    await peer.stop()


asyncio.run(main())
