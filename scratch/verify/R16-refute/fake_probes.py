"""Browser-free probes for SEED-C1, SEED-C2, SEED-C3 using an in-process websockets server."""

import asyncio
import json
import sys

import websockets
import websockets.asyncio.server

import zendriver
from zendriver import cdp
from zendriver.core.connection import Connection

print("zendriver from", zendriver.__file__, "python", sys.version.split()[0])


class FakePeer:
    def __init__(self) -> None:
        self.connections = 0
        self.open = 0
        self.ignore: set[str] = set()
        self.close_after_first = False
        self.server = None
        self.peers = []

    async def handler(self, ws) -> None:
        self.connections += 1
        self.open += 1
        self.peers.append(ws)
        try:
            async for raw in ws:
                msg = json.loads(raw)
                if msg["method"] in self.ignore:
                    continue
                await ws.send(json.dumps({"id": msg["id"], "result": {}}))
                if self.close_after_first:
                    self.close_after_first = False
                    await ws.close(1011, "server side close")
                    return
        except websockets.exceptions.ConnectionClosed:
            pass
        finally:
            self.open -= 1

    async def start(self) -> str:
        self.server = await websockets.asyncio.server.serve(self.handler, "127.0.0.1", 0)
        port = self.server.sockets[0].getsockname()[1]
        return f"ws://127.0.0.1:{port}/devtools/browser/fake"

    async def stop(self) -> None:
        self.server.close()
        await self.server.wait_closed()


def cmd():
    return cdp.target.set_discover_targets(discover=True)


async def probe_c1() -> None:
    print("\n=== SEED-C1: ConnectionClosed leaves websocket set, no reconnect ===")
    peer = FakePeer()
    url = await peer.start()
    conn = Connection(url)
    try:
        peer.close_after_first = True
        await asyncio.wait_for(conn.send(cmd()), 5)
        for _ in range(50):
            if conn.listener is not None and not conn.listener.running:
                break
            await asyncio.sleep(0.05)
        print("listener running after server close:", conn.listener.running)
        print("conn.websocket is None:", conn.websocket is None, " conn.closed:", conn.closed)
        for i in range(3):
            try:
                await asyncio.wait_for(conn.send(cmd()), 5)
                print(f"send #{i}: succeeded")
            except asyncio.TimeoutError:
                print(f"send #{i}: HANG (outer timeout)")
            except Exception as e:  # noqa
                print(f"send #{i}: raised {type(e).__name__}: {e}")
        print("server saw connections:", peer.connections, "(1 => never reconnected)")

        # contrast: after a deliberate aclose(), send() reconnects
        await conn.aclose()
        await asyncio.wait_for(conn.send(cmd()), 5)
        print("after aclose()+send(): server connections:", peer.connections, "(2 => aclose path reconnects)")
    finally:
        await conn.aclose()
        await peer.stop()


async def probe_c2() -> None:
    print("\n=== SEED-C2: aclose() during an in-progress connect ===")
    peer = FakePeer()
    url = await peer.start()
    real_connect = websockets.connect

    async def slow_connect(*a, **kw):
        await asyncio.sleep(0.3)
        return await real_connect(*a, **kw)

    websockets.connect = slow_connect
    conn = Connection(url)
    try:
        t = asyncio.create_task(conn.send(cmd()))
        await asyncio.sleep(0.1)
        print("before aclose: websocket is None:", conn.websocket is None)
        await conn.aclose()
        print("aclose() returned; websocket is None:", conn.websocket is None)
        try:
            await asyncio.wait_for(t, 5)
            print("pending send after aclose(): SUCCEEDED (connection opened after the close)")
        except Exception as e:  # noqa
            print("pending send after aclose(): raised", type(e).__name__, e)
        await asyncio.sleep(0.2)
        print("after: websocket is None:", conn.websocket is None,
              " listener running:", conn.listener.running if conn.listener else None,
              " server open sockets:", peer.open)
    finally:
        websockets.connect = real_connect
        await conn.aclose()
        await asyncio.sleep(0.1)
        print("after a 2nd aclose(): server open sockets:", peer.open)
        await peer.stop()


async def probe_c3() -> None:
    print("\n=== SEED-C3: cancelled send leaves its Transaction in mapper ===")
    peer = FakePeer()
    url = await peer.start()
    conn = Connection(url)
    try:
        await asyncio.wait_for(conn.send(cmd()), 5)
        peer.ignore.add("Runtime.evaluate")
        for i in range(5):
            try:
                await asyncio.wait_for(conn.send(cdp.runtime.evaluate("1")), 0.2)
            except asyncio.TimeoutError:
                pass
        print("mapper size after 5 timed-out never-answered sends:", len(conn.mapper),
              [ (k, v.cancelled()) for k, v in conn.mapper.items()])
        # answered-late case: the reply pops it
        peer.ignore.clear()
        await asyncio.wait_for(conn.send(cmd()), 5)
        print("mapper size after a normal command:", len(conn.mapper), "(still there: never-answered ones stay)")
    finally:
        await conn.aclose()
        print("mapper size after aclose():", len(conn.mapper))
        await peer.stop()


async def main() -> None:
    await probe_c1()
    await probe_c2()
    await probe_c3()


asyncio.run(main())
