import asyncio, sys, functools, logging
import zendriver
from zendriver import cdp
from zendriver.core.connection import Connection
from fakepeer import FakePeer, GOOD_TARGET, VERSION
print("zendriver from", zendriver.__file__, "python", sys.version.split()[0])

EVENT = {"method": "Target.targetCreated", "params": {"targetInfo": GOOD_TARGET}}
beh = {"Browser.getVersion": lambda m: [EVENT, {"id": m["id"], "result": VERSION}]}

async def bad_async_noarg(): pass
def bad_sync_noarg(): pass
async def raises_inside(ev): raise RuntimeError("boom inside handler")
async def needs_three(a, b, c): pass
class AsyncCallable:
    async def __call__(self): pass

calls = []
async def good(ev): calls.append(ev)

CASES = [
    ("async def h() (wrong arity)", bad_async_noarg),
    ("def h() sync (wrong arity)", bad_sync_noarg),
    ("lambda: None", lambda: None),
    ("async handler raising in body", raises_inside),
    ("async def h(a,b,c)", needs_three),
    ("partial(async f, extra)", functools.partial(good, 1)),
    ("instance with async __call__()", AsyncCallable()),
]

async def run(name, h):
    async with FakePeer(beh) as peer:
        conn = Connection(peer.url)
        conn.add_handler(cdp.target.TargetCreated, good)
        conn.add_handler(cdp.target.TargetCreated, h)
        await conn.aopen()
        lst = conn.listener
        t = asyncio.create_task(conn.send(cdp.browser.get_version()))
        done, _ = await asyncio.wait({t}, timeout=3)
        print(f"[{name}] get_version done within 3s={bool(done)} | listener running={lst.running} exc={(lst.task.exception() if lst.task.done() else None)!r:.90}")
        if not done:
            stack = []
            t.print_stack(limit=3, file=sys.stdout); sys.stdout.flush()
            # does a later send recover the in-flight one?
            r2 = await asyncio.wait_for(conn.send(cdp.target.set_discover_targets(discover=True)), 3)
            await asyncio.sleep(0.1)
            print(f"    later send ok={r2!r}; original now done={t.done()} ; listener running={conn.listener.running}")
        t.cancel(); await asyncio.gather(t, return_exceptions=True)
        await conn.aclose()

async def main():
    for c in CASES:
        await run(*c)
asyncio.run(asyncio.wait_for(main(), 60))
