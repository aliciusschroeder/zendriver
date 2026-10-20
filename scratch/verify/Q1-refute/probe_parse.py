import asyncio, sys, gc
import zendriver
from zendriver import cdp
from zendriver.core.connection import Connection, ProtocolException
from fakepeer import FakePeer, GOOD_TARGET, VERSION
print("zendriver from", zendriver.__file__, "python", sys.version.split()[0])

def bad_cookie(m):
    c = {"name":"a","value":"b","domain":"x","path":"/","expires":-1,"size":2,"httpOnly":False,
         "secure":False,"session":True,"sameSite":"SomeFutureValue","priority":"Medium",
         "sourceScheme":"Secure","sourcePort":443}
    return [{"id": m["id"], "result": {"cookies": [c]}}]

def custom_raise():
    j = yield {"method": "Runtime.evaluate", "params": {"expression": "1"}}
    return j["x"]

def custom_yield_twice():
    j = yield {"method": "Runtime.evaluate", "params": {"expression": "1"}}
    yield {"method": "x"}

CASES = [
  ("getTargetInfo missing key", {"Target.getTargetInfo": lambda m: [{"id": m["id"], "result": {}}]}, lambda: cdp.target.get_target_info()),
  ("getCookies unknown enum", {"Storage.getCookies": bad_cookie}, lambda: cdp.storage.get_cookies()),
  ("reply without result key", {"Browser.getVersion": lambda m: [{"id": m["id"]}]}, lambda: cdp.browser.get_version()),
  ("custom generator raises", {"Runtime.evaluate": lambda m: [{"id": m["id"], "result": {"a": 1}}]}, custom_raise),
  ("custom generator yields twice", {"Runtime.evaluate": lambda m: [{"id": m["id"], "result": {"a": 1}}]}, custom_yield_twice),
  ("control: error reply", {"Browser.getVersion": lambda m: [{"id": m["id"], "error": {"code": -32000, "message": "nope"}}]}, lambda: cdp.browser.get_version()),
]

async def run_case(name, beh, mk):
    async with FakePeer(beh) as peer:
        conn = Connection(peer.url)
        await conn.aopen()
        lst = conn.listener
        t = asyncio.create_task(conn.send(mk()))
        done, _ = await asyncio.wait({t}, timeout=3)
        res = "HUNG (3s)" if not done else (f"raised {type(t.exception()).__name__}: {str(t.exception())[:60]!r}" if t.exception() else f"returned {t.result()!r}"[:80])
        lexc = lst.task.exception() if lst.task.done() else None
        print(f"[{name}] send(): {res} | listener done={lst.task.done()} exc={lexc!r:.70} | mapper={dict(conn.mapper)}")
        if not done:
            await conn.aclose()
            await asyncio.sleep(0.2)
            print(f"    after aclose(): send still pending={not t.done()}")
            t.cancel()
            try: await t
            except BaseException: pass
        else:
            await conn.aclose()

async def concurrent_case():
    # bad reply for cmd A, good reply for cmd B queued right behind it
    async with FakePeer({"Target.getTargetInfo": lambda m: [("delay", 0.3), {"id": m["id"], "result": {}}],
                         "Browser.getVersion": lambda m: [("delay", 0.6), {"id": m["id"], "result": VERSION}]}) as peer:
        conn = Connection(peer.url)
        await conn.aopen()
        a = asyncio.create_task(conn.send(cdp.target.get_target_info()))
        b = asyncio.create_task(conn.send(cdp.browser.get_version()))
        await asyncio.wait({a, b}, timeout=3)
        print(f"[concurrent] bad A done={a.done()} good B done={b.done()} listener running={conn.listener.running}")
        # a later send restarts the listener -> B gets its (already buffered) reply
        r = await asyncio.wait_for(conn.send(cdp.browser.get_version()), 3)
        await asyncio.sleep(0.2)
        print(f"[concurrent] after later send: B done={b.done()} A done={a.done()}")
        for t in (a, b):
            t.cancel()
        await asyncio.gather(a, b, return_exceptions=True)
        await conn.aclose()

async def main():
    for c in CASES:
        await run_case(*c)
    await concurrent_case()

asyncio.run(asyncio.wait_for(main(), 60))
