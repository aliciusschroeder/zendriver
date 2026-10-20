import asyncio, sys, json
import zendriver
from zendriver import cdp
from zendriver.core.connection import Connection
from fakepeer import FakePeer, VERSION
print("zendriver from", zendriver.__file__, "python", sys.version.split()[0])

async def case(name, beh, extra=None):
    async with FakePeer(beh) as peer:
        conn = Connection(peer.url)
        await conn.aopen()
        lst = conn.listener
        if extra: await extra(conn)
        t = asyncio.create_task(conn.send(cdp.browser.get_version()))
        done, _ = await asyncio.wait({t}, timeout=3)
        print(f"[{name}] send done={bool(done)} listener running={lst.running} exc={(lst.task.exception() if lst.task.done() else None)!r:.80} mapper_ids={list(conn.mapper)}")
        if not done:
            ok = await asyncio.wait_for(conn.send(cdp.target.set_discover_targets(discover=True)), 3)
            await asyncio.sleep(0.2)
            print(f"    later send ok; original send now done={t.done()}")
            await conn.aclose(); await asyncio.sleep(0.1)
            print(f"    after aclose original done={t.done()} exc={(t.exception() if t.done() and not t.cancelled() else None)!r:.60}")
        t.cancel(); await asyncio.gather(t, return_exceptions=True)
        await conn.aclose()

async def second_reader(conn):
    # simulate a second concurrent recv() on the same websocket (ConcurrencyError path)
    conn._extra = asyncio.create_task(conn.websocket.recv())
    await asyncio.sleep(0.3)

async def main():
    await case("non-JSON frame before reply", {"Browser.getVersion": lambda m: ["this is not json", {"id": m["id"], "result": VERSION}]})
    await case("non-JSON frame instead of reply", {"Browser.getVersion": lambda m: ["not json"]})
    await case("second concurrent recv (ConcurrencyError)", {"Browser.getVersion": lambda m: [("delay", 0.3), {"id": m["id"], "result": VERSION}]}, second_reader)
asyncio.run(asyncio.wait_for(main(), 60))
