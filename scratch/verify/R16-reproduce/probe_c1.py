"""SEED-C1: after the peer closes the websocket, does aopen/send reconnect?"""

import asyncio
import sys

sys.path.insert(0, __file__.rsplit("/", 1)[0])

import zendriver
from zendriver import cdp
from zendriver.core.connection import Connection

from fake_cdp import FakeCDP

print("zendriver from", zendriver.__file__, "python", sys.version.split()[0])


async def main() -> None:
    peer = await FakeCDP().start()
    conn = Connection(peer.url)
    await conn.send(cdp.runtime.run_if_waiting_for_debugger())
    print("1st send ok; server connections:", len(peer.connections))
    first_listener = conn.listener

    await peer.close_all(code=1001)  # browser side closes the socket
    for _ in range(50):
        if not first_listener.running:
            break
        await asyncio.sleep(0.02)
    print("listener running after peer close:", first_listener.running)
    print("conn.websocket is None:", conn.websocket is None)
    print("conn.closed:", conn.closed)
    print("websocket state:", conn.websocket.state if conn.websocket else None)

    # peer is still accepting new connections; a reconnecting aopen would succeed
    try:
        await asyncio.wait_for(
            conn.send(cdp.runtime.run_if_waiting_for_debugger()), timeout=5
        )
        print("2nd send OK (reconnected); server connections:", len(peer.connections))
    except Exception as e:
        print("2nd send raised:", type(e).__name__, e)
        print("server connections after 2nd send:", len(peer.connections),
              "handshakes:", peer.handshakes_started)

    try:
        await asyncio.wait_for(conn.aopen(), 5)
        print("explicit aopen() returned; websocket state:", conn.websocket.state,
              "server connections:", len(peer.connections))
    except Exception as e:
        print("aopen raised", type(e).__name__, e)

    await conn.aclose()
    await peer.stop()


asyncio.run(main())
