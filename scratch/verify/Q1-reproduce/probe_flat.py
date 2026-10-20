"""A2.4 with a fake peer: browser listener dead -> flat-session tab sends hang.
Also: Connection.wait() hang, and ConcurrencyError variant of SEED-L1."""

import asyncio
import io
import json
import sys
import types

import websockets

import zendriver
from zendriver import cdp
from zendriver.core.connection import Connection, Listener

from fakepeer import FakePeer, TARGET_INFO

print("zendriver from", zendriver.__file__, "python", sys.version.split()[0])


def stack_tail(task):
    s = io.StringIO()
    task.print_stack(file=s)
    return s.getvalue().strip().splitlines()[-2:]


def bad_custom():
    j = yield {"method": "Custom.whatever", "params": {}}
    return j["nope"]


async def flat():
    peer = await FakePeer().start()
    bconn = Connection(peer.url)
    owner = types.SimpleNamespace(connection=bconn, config=None)
    tab = Connection(peer.url, target=cdp.target.TargetInfo.from_json(TARGET_INFO), _owner=owner)
    r = await asyncio.wait_for(tab.send(cdp.runtime.evaluate("2+2")), 3)
    print("[A2.4] tab send before:", r[0].value, "session", tab.session_id)
    try:
        await asyncio.wait_for(bconn.send(bad_custom()), 3)
    except asyncio.TimeoutError:
        print("[A2.4] browser-level bad send hung 3s; browser listener running:", bconn.listener.running,
              "exc:", repr(bconn.listener.task.exception()))
    t = asyncio.create_task(tab.send(cdp.runtime.evaluate("2+2")))
    try:
        await asyncio.wait_for(asyncio.shield(t), 3)
        print("[A2.4] tab send returned -> NOT reproduced")
    except asyncio.TimeoutError:
        print("[A2.4] tab send done in 3s:", t.done(), "| tab listener running:", tab.listener.running,
              "| tab inbox size:", tab._inbox.qsize(), "| browser listener running:", bconn.listener.running,
              "| peer got the evaluate:", sum(1 for m in peer.received if m.get("sessionId") == "S1"))
        print("   stuck at:", stack_tail(t))
    # a second tab send, after waiting longer, still hangs
    try:
        await asyncio.wait_for(tab.send(cdp.runtime.evaluate("3+3")), 3)
        print("[A2.4] second tab send ok")
    except asyncio.TimeoutError:
        print("[A2.4] second tab send also hung 3s")
    await asyncio.wait_for(bconn.send(cdp.browser.get_version()), 3)
    await asyncio.sleep(0.3)
    print("[A2.4] after a browser-level send: tab send done:", t.done(), "value:", t.result()[0].value if t.done() else None)
    await tab.aclose()
    await bconn.aclose()
    await peer.stop()


async def conn_wait_hang():
    TC = json.dumps({"method": "Target.targetCreated", "params": {"targetInfo": TARGET_INFO}})

    async def stream_then_bad(peer, ws, msg):
        for _ in range(20):
            await ws.send(TC)
            await asyncio.sleep(0.03)
        await ws.send(peer.reply(msg, {}))
        for _ in range(3):
            await ws.send(TC)

    def custom():
        j = yield {"method": "Custom.streamThenBad", "params": {}}
        return j["nope"]

    peer = await FakePeer({"Custom.streamThenBad": stream_then_bad}).start()
    conn = Connection(peer.url, target=cdp.target.TargetInfo.from_json(TARGET_INFO))
    await conn.aopen()
    bad = asyncio.create_task(conn.send(custom()))
    await asyncio.sleep(0.1)
    w = asyncio.create_task(conn.wait())  # Connection.wait(), t=None
    try:
        await asyncio.wait_for(asyncio.shield(w), 4)
        print("[wait] Connection.wait() returned -> not reproduced")
    except asyncio.TimeoutError:
        print("[wait] Connection.wait() still blocked after 4s; listener running:", conn.listener.running,
              "exc:", repr(conn.listener.task.exception()))
        print("   stuck at:", stack_tail(w))
    for x in (bad, w):
        x.cancel()
        try:
            await x
        except BaseException:
            pass
    await conn.aclose()
    await peer.stop()


async def concurrency_variant():
    peer = await FakePeer().start()
    conn = Connection(peer.url)
    conn.websocket = await websockets.connect(peer.url)
    rogue = asyncio.create_task(conn.websocket.recv())
    await asyncio.sleep(0.05)
    conn.listener = Listener(conn)
    await asyncio.sleep(0.2)
    print("[SEED-L1 ConcurrencyError] listener running:", conn.listener.running, "exc:", repr(conn.listener.task.exception()))
    rogue.cancel()
    try:
        await rogue
    except BaseException:
        pass
    await conn.aclose()
    await peer.stop()


async def main():
    for f in (flat, conn_wait_hang, concurrency_variant):
        await asyncio.wait_for(f(), 40)


asyncio.run(main())
