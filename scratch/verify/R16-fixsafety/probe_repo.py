import asyncio, sys
sys.path.insert(0, sys.argv[1])
import test_r16_connection_close_state as t
from zendriver import cdp
from zendriver.core.connection import Connection

async def c1():
    async with t.FakeCDP(close_after_first_reply=True) as peer:
        conn = Connection(peer.url)
        await asyncio.wait_for(conn.send(cdp.target.get_target_info()), 5)
        await t._until(lambda: not conn.listener.running)
        for i in range(3):
            try:
                r = await asyncio.wait_for(conn.send(cdp.target.get_target_info()), 5)
                print("C1 send", i, "ok", r.target_id, "connections", peer.connections)
            except Exception as e:
                print("C1 send", i, "raised", type(e).__name__, e, "| closed=", conn.closed, "connections", peer.connections)
        await conn.aclose()

async def c2():
    async with t.FakeCDP(handshake_delay=0.5) as peer:
        conn = Connection(peer.url)
        opener = asyncio.ensure_future(conn.aopen())
        await asyncio.sleep(0.15)
        await conn.aclose()
        await opener
        await asyncio.sleep(1.0)
        print("C2 after aclose+aopen: closed=", conn.closed, "listener running=", conn.listener.running, "server open conns=", peer.open_connections)
        await conn.aclose()

asyncio.run(c1()); asyncio.run(c2())
