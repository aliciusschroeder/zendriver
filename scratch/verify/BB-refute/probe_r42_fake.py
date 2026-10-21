"""Browser-free checks for R42: shared exception on close, remove_handlers(module)."""
import asyncio
import json
import sys

import websockets
import websockets.asyncio.server

import zendriver
from zendriver import cdp
from zendriver.core.connection import Connection, ProtocolException

print("zendriver from", zendriver.__file__, sys.version.split()[0], "websockets", websockets.__version__)


async def peer(ws):
    # never answers anything
    async for msg in ws:
        pass


async def shared_exc(close_how):
    server = await websockets.asyncio.server.serve(peer, "127.0.0.1", 0)
    port = server.sockets[0].getsockname()[1]
    conn = Connection(f"ws://127.0.0.1:{port}")
    await conn.aopen()
    tasks = [
        asyncio.ensure_future(conn.send(cdp.target.get_targets())),
        asyncio.ensure_future(conn.send(cdp.target.create_target(url="https://secret.example/?token=abc"))),
        asyncio.ensure_future(conn.send(cdp.browser.get_version())),
    ]
    await asyncio.sleep(0.3)
    if close_how == "aclose":
        await conn.aclose()
    else:
        # peer-side close: the listener path
        for c in list(server.connections):
            await c.close()
    res = await asyncio.wait_for(asyncio.gather(*tasks, return_exceptions=True), 5)
    print(f"[{close_how}] types:", [type(r).__name__ for r in res])
    print(f"[{close_how}] same object 0/1/2:", res[0] is res[1], res[1] is res[2])
    print(f"[{close_how}] str(res[0]) = {str(res[0])!r}")
    server.close()
    await server.wait_closed()
    if conn.websocket is not None:
        await conn.aclose()


async def remove_module():
    conn = Connection("ws://127.0.0.1:9/unused")

    def h(ev):
        pass

    conn.add_handler(cdp.network, h)
    count = lambda: sum(1 for k, v in conn.handlers.items() if h in v)
    print("after add_handler(cdp.network, h):", count())
    conn.remove_handlers(cdp.network, h)
    print("after remove_handlers(cdp.network, h):", count())
    conn.remove_handlers(cdp.network)
    print("after remove_handlers(cdp.network):", count(), "| module key present:", cdp.network in conn.handlers)


async def main():
    await shared_exc("aclose")
    await shared_exc("peer-close")
    await remove_module()


asyncio.run(main())
