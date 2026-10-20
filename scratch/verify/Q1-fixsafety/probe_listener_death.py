import asyncio, sys, types
sys.path.insert(0, sys.argv[1])  # dir containing the test module
import pytest
import test_q1_listener_robustness as T
import websockets
from zendriver import cdp
from zendriver.core.connection import Connection

async def scenario(name, responder, cmd, handlers=()):
    async def connect(*a, **k):
        return T.ScriptedWebSocket(responder)
    websockets.connect = connect
    conn = Connection("ws://fake/devtools/browser/x")
    for ev, h in handlers:
        conn.add_handler(ev, h)
    await conn.aopen()
    listener = conn.listener
    task = asyncio.ensure_future(conn.send(cmd))
    done, _ = await asyncio.wait({task}, timeout=2)
    exc = listener.task.exception() if listener.task.done() else None
    print(f"{name}: send finished={bool(done)} | first listener done={listener.task.done()} exc={exc!r} | mapper={conn.mapper}")
    task.cancel()
    await asyncio.wait({task}, timeout=1)
    await conn.aclose()

async def main():
    import zendriver; print("zendriver:", zendriver.__file__)
    ok = lambda c: [T.reply(c, T.default_result(c["method"]))]
    await scenario("missing-key", lambda c: [T.reply(c, {})], cdp.target.get_target_info())
    def custom():
        j = yield {"method": "Runtime.evaluate", "params": {"expression": "1"}}
        return j["notThere"]
    await scenario("custom-gen", ok, custom())
    def bad_frame(c):
        return ["not json", T.reply(c, T.default_result(c["method"]))] if c["method"] == "Browser.getVersion" else ok(c)
    await scenario("non-json", bad_frame, cdp.browser.get_version())
    def ev(c):
        f = []
        if c["method"] == "Browser.getVersion":
            f.append({"method": "Target.targetCreated", "params": {"targetInfo": dict(T.TARGET_INFO)}})
        return f + ok(c)
    async def bad(): pass
    await scenario("bad-handler", ev, cdp.browser.get_version(), [(cdp.target.TargetCreated, bad)])

asyncio.run(main())
