"""A1.1 / A2.3 / B15.1: reply that the parser rejects -> listener dies, tx lost, send hangs."""

import asyncio
import io
import json
import logging
import sys

sys.path.insert(0, sys.path[0])
import zendriver
from zendriver import cdp
from zendriver.core.connection import Connection

from fakepeer import FakePeer

print("zendriver from", zendriver.__file__, "python", sys.version.split()[0])

log_buf = io.StringIO()
h = logging.StreamHandler(log_buf)
h.setLevel(logging.WARNING)
logging.getLogger().addHandler(h)
logging.getLogger().setLevel(logging.DEBUG)


def custom_keyerror():
    j = yield {"method": "Runtime.evaluate", "params": {"expression": "1"}}
    return j["x"]


def custom_two_yields():
    j = yield {"method": "Runtime.evaluate", "params": {"expression": "1"}}
    yield {"method": "Runtime.evaluate", "params": {"expression": "2"}}
    return j


COOKIE = {
    "name": "a",
    "value": "b",
    "domain": "x.test",
    "path": "/",
    "size": 2,
    "httpOnly": False,
    "secure": False,
    "session": True,
    "priority": "Medium",
    "sourceScheme": "Secure",
    "sourcePort": 443,
    "expires": -1,
    "sameSite": "SomeFutureValue",
}


def make_override(result_obj, omit_result=False):
    async def fn(peer, ws, msg):
        if omit_result:
            await ws.send(json.dumps({"id": msg["id"]}))
        else:
            await ws.send(peer.reply(msg, result_obj))

    return fn


CASES = [
    ("getTargetInfo result={}", "Target.getTargetInfo", make_override({}), lambda: cdp.target.get_target_info()),
    (
        "Runtime.evaluate bad exceptionDetails",
        "Runtime.evaluate",
        make_override({"result": {"type": "object"}, "exceptionDetails": {"bogus": 1}}),
        lambda: cdp.runtime.evaluate("1"),
    ),
    ("Storage.getCookies unknown sameSite", "Storage.getCookies", make_override({"cookies": [COOKIE]}), lambda: cdp.storage.get_cookies()),
    ("custom generator j['x']", "Runtime.evaluate", None, custom_keyerror),
    ("custom generator yields twice", "Runtime.evaluate", None, custom_two_yields),
    ("reply without 'result' key", "Target.getTargetInfo", make_override(None, omit_result=True), lambda: cdp.target.get_target_info()),
]


async def run_case(name, method, override, mk):
    peer = await FakePeer({method: override} if override else {}).start()
    conn = Connection(peer.url)
    await conn.aopen()
    old_listener = conn.listener
    task = asyncio.create_task(conn.send(mk()))
    try:
        r = await asyncio.wait_for(asyncio.shield(task), 3)
        print(f"[{name}] send returned {r!r} (NOT reproduced)")
        await conn.aclose(); await peer.stop()
        return
    except asyncio.TimeoutError:
        pass
    except Exception as e:
        print(f"[{name}] send RAISED {type(e).__name__}: {e} (bug not reproduced)")
        await conn.aclose(); await peer.stop()
        return
    lt = old_listener.task
    print(f"[{name}] send done within 3s: {task.done()} | listener running: {old_listener.running}"
          f" | listener exc: {lt.exception()!r} | mapper size: {len(conn.mapper)}")
    print("  stuck task stack:")
    s = io.StringIO(); task.print_stack(file=s); print("   ", s.getvalue().strip().splitlines()[-2:])
    # a later unrelated send recreates a listener; the lost tx stays pending
    v = await asyncio.wait_for(conn.send(cdp.browser.get_version()), 3)
    await asyncio.sleep(0.3)
    print(f"  later get_version ok={v[1]!r}; new listener running={conn.listener.running};"
          f" original send done={task.done()}")
    await conn.aclose()
    await asyncio.sleep(0.2)
    print(f"  after aclose(): original send done={task.done()}")
    task.cancel()
    try:
        await task
    except BaseException as e:
        print(f"  (cleanup: cancelled -> {type(e).__name__})")
    await peer.stop()


async def main():
    for c in CASES:
        await asyncio.wait_for(run_case(*c), 30)
    print("WARNING+ log records emitted by zendriver:", repr(log_buf.getvalue()[:300]))


asyncio.run(main())
