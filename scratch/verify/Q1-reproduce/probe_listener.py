"""SEED-L1 (non-parse exceptions from _receive_message), B15.4 (bad-arity handler),
plus secondary effects: other in-flight sends hang, wait() on idle hangs."""

import asyncio
import io
import json
import sys

import zendriver
from zendriver import cdp
from zendriver.core.connection import Connection

from fakepeer import FakePeer, TARGET_INFO

print("zendriver from", zendriver.__file__, "python", sys.version.split()[0])

TARGET_CREATED = json.dumps({"method": "Target.targetCreated", "params": {"targetInfo": TARGET_INFO}})


def stack_tail(task):
    s = io.StringIO()
    task.print_stack(file=s)
    return s.getvalue().strip().splitlines()[-2:]


async def check_hang(name, conn, coro, extra_after=None):
    old = conn.listener
    task = asyncio.create_task(coro)
    try:
        r = await asyncio.wait_for(asyncio.shield(task), 3)
        print(f"[{name}] returned {r!r} -> NOT reproduced")
        return task
    except asyncio.TimeoutError:
        pass
    print(f"[{name}] done within 3s: {task.done()} | old listener running: {old.running}"
          f" | exc: {old.task.exception()!r} | mapper: {list(conn.mapper)}")
    print("   stuck at:", stack_tail(task))
    return task


async def seed_nonjson():
    async def bad_frame(peer, ws, msg):
        await ws.send("this is not json")
        await ws.send(peer.reply(msg, {"protocolVersion": "1", "product": "P", "revision": "r", "userAgent": "u", "jsVersion": "j"}))

    peer = await FakePeer({"Browser.getVersion": bad_frame}).start()
    conn = Connection(peer.url)
    await conn.aopen()
    t = await check_hang("SEED-L1 non-JSON frame", conn, conn.send(cdp.browser.get_version()))
    r = await asyncio.wait_for(conn.send(cdp.target.get_target_info()), 3)
    await asyncio.sleep(0.2)
    print(f"   after a later send (ok={r.target_id}): original done={t.done()} result={t.result()[1] if t.done() else None}")
    await conn.aclose(); await peer.stop()


async def seed_detached_malformed():
    async def bad_frame(peer, ws, msg):
        await ws.send(json.dumps({"method": "Target.detachedFromTarget", "params": {"targetId": "T9"}}))
        await ws.send(peer.reply(msg, {"protocolVersion": "1", "product": "P", "revision": "r", "userAgent": "u", "jsVersion": "j"}))

    peer = await FakePeer({"Browser.getVersion": bad_frame}).start()
    conn = Connection(peer.url)
    await conn.aopen()
    t = await check_hang("SEED-L1 detachedFromTarget w/o sessionId", conn, conn.send(cdp.browser.get_version()))
    t.cancel()
    await conn.aclose(); await peer.stop()


async def seed_concurrency():
    # a second reader on the websocket -> websockets ConcurrencyError raised inside _receive_message
    async def slow(peer, ws, msg):
        await asyncio.sleep(1.0)
        await ws.send(peer.reply(msg, {"protocolVersion": "1", "product": "P", "revision": "r", "userAgent": "u", "jsVersion": "j"}))

    peer = await FakePeer({"Browser.getVersion": slow}).start()
    conn = Connection(peer.url)
    await conn.aopen()
    rogue = asyncio.create_task(conn.websocket.recv())  # holds the recv slot
    await asyncio.sleep(0.3)
    t = await check_hang("SEED-L1 ConcurrencyError (2nd reader)", conn, conn.send(cdp.browser.get_version()))
    rogue.cancel(); t.cancel()
    for x in (rogue, t):
        try:
            await x
        except BaseException:
            pass
    await conn.aclose(); await peer.stop()


async def b15_4_bad_handler():
    async def event_then_reply(peer, ws, msg):
        await ws.send(TARGET_CREATED)
        await ws.send(peer.reply(msg, {"protocolVersion": "1", "product": "P", "revision": "r", "userAgent": "u", "jsVersion": "j"}))

    peer = await FakePeer({"Browser.getVersion": event_then_reply}).start()
    conn = Connection(peer.url)
    await conn.aopen()
    fired = []

    async def bad_handler():  # wrong arity
        fired.append("bad")

    async def good_handler(ev):
        fired.append("good")

    conn.add_handler(cdp.target.TargetCreated, bad_handler)
    conn.add_handler(cdp.target.TargetCreated, good_handler)
    t = await check_hang("B15.4 async handler w/ wrong arity", conn, conn.send(cdp.browser.get_version()))
    print("   handlers fired:", fired)
    r = await asyncio.wait_for(conn.send(cdp.target.get_target_info()), 3)
    await asyncio.sleep(0.2)
    print(f"   after later send: original done={t.done()} ; listener running={conn.listener.running}")
    # next event kills the revived listener again
    t2 = await check_hang("B15.4 second round", conn, conn.send(cdp.browser.get_version()))
    t2.cancel()
    try:
        await t2
    except BaseException:
        pass
    # sync handler w/ wrong arity, for contrast
    conn.remove_handlers()

    def bad_sync():
        pass

    conn.add_handler(cdp.target.TargetCreated, bad_sync)
    try:
        r = await asyncio.wait_for(conn.send(cdp.browser.get_version()), 3)
        print(f"   [contrast] SYNC wrong-arity handler: send ok ({r[1]}), listener running={conn.listener.running}")
    except asyncio.TimeoutError:
        print("   [contrast] SYNC wrong-arity handler: also hangs")
    await conn.aclose(); await peer.stop()


async def other_inflight_and_wait():
    # cmd1 gets a bad reply; cmd2's (good) reply is queued right after -> cmd2 also hangs
    held = {}

    async def bad_after_good(peer, ws, msg):
        held["bad"] = msg
        await asyncio.sleep(0.05)
        await ws.send(peer.reply(msg, {}))  # KeyError('targetInfo')

    peer = await FakePeer({"Target.getTargetInfo": bad_after_good}).start()
    conn = Connection(peer.url)
    await conn.aopen()
    t1 = asyncio.create_task(conn.send(cdp.target.get_target_info()))

    async def delayed_version(peer_, ws, msg):
        await asyncio.sleep(0.15)
        await ws.send(peer_.reply(msg, {"protocolVersion": "1", "product": "P", "revision": "r", "userAgent": "u", "jsVersion": "j"}))

    peer.overrides["Browser.getVersion"] = delayed_version
    await asyncio.sleep(0.01)
    t2 = await check_hang("other in-flight cmd2 (good reply queued behind bad one)", conn, conn.send(cdp.browser.get_version()))
    print("   cmd1 done:", t1.done())
    for x in (t1, t2):
        x.cancel()
        try:
            await x
        except BaseException:
            pass
    await conn.aclose(); await peer.stop()


async def idle_wait_hang():
    # wait() blocked on listener.idle while events stream; then the bad reply kills the listener
    async def stream_then_bad(peer, ws, msg):
        for _ in range(10):
            await ws.send(TARGET_CREATED)
            await asyncio.sleep(0.03)
        await ws.send(peer.reply(msg, {}))  # bad reply for custom method
        for _ in range(3):
            await ws.send(TARGET_CREATED)

    def custom():
        j = yield {"method": "Custom.streamThenBad", "params": {}}
        return j["nope"]

    peer = await FakePeer({"Custom.streamThenBad": stream_then_bad}).start()
    conn = Connection(peer.url)
    await conn.aopen()
    old = conn.listener
    bad = asyncio.create_task(conn.send(custom()))
    await asyncio.sleep(0.1)
    w = asyncio.create_task(conn.listener.idle.wait())  # what Connection.wait() awaits after update_target
    w2 = None
    try:
        await asyncio.wait_for(asyncio.shield(w), 3)
        print("[idle wait] idle.wait() returned -> not reproduced")
    except asyncio.TimeoutError:
        print(f"[idle wait] listener.idle.wait() still blocked after 3s; old listener running={old.running}, exc={old.task.exception()!r}")
    for x in (bad, w):
        x.cancel()
        try:
            await x
        except BaseException:
            pass
    await conn.aclose(); await peer.stop()


async def main():
    for f in (seed_nonjson, seed_detached_malformed, seed_concurrency, b15_4_bad_handler, other_inflight_and_wait, idle_wait_hang):
        await asyncio.wait_for(f(), 40)


asyncio.run(main())
