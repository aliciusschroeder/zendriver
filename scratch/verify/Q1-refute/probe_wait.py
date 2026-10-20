import asyncio, sys
import zendriver
from zendriver import cdp
from zendriver.core.connection import Connection
from fakepeer import FakePeer, GOOD_TARGET
print("zendriver from", zendriver.__file__, "python", sys.version.split()[0])
beh = {"Target.getTargetInfo": lambda m: [{"id": m["id"], "result": {"targetInfo": GOOD_TARGET}}],
       "Target.getTargets": lambda m: [{"id": m["id"], "result": {}}]}  # bad: missing targetInfos
async def main():
    async with FakePeer(beh) as peer:
        conn = Connection(peer.url)
        await conn.aopen()
        await asyncio.sleep(0.3)
        w = asyncio.create_task(conn.wait())
        b = asyncio.create_task(conn.send(cdp.target.get_targets()))
        done, _ = await asyncio.wait({w, b}, timeout=3)
        print(f"wait() done={w.done()} bad send done={b.done()} listener running={conn.listener.running} idle set={conn.listener.idle.is_set()}")
        w2 = asyncio.create_task(conn.wait())
        await asyncio.wait({w2}, timeout=3)
        print(f"a NEW wait() after the death done={w2.done()} (its update_target send revives the listener)")
        await asyncio.sleep(0.3)
        print(f"original wait() done now={w.done()}")
        for t in (w, b, w2): t.cancel()
        await asyncio.gather(w, b, w2, return_exceptions=True)
        await conn.aclose()
asyncio.run(asyncio.wait_for(main(), 30))
