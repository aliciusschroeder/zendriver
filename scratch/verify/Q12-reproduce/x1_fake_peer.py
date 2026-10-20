"""
Q12 / SEED-X1 reproducer: CancelledError swallowed by the bare except in
Connection._register_handlers around `await self.send(domain_mod.enable(), _is_update=True)`.

Fake CDP peer: drops replies for methods in DROP, answers everything else.
"""
import asyncio
import json
import sys
import time

import websockets
from websockets.asyncio.server import serve

import zendriver
from zendriver import cdp
from zendriver.core.connection import Connection

print("python", sys.version.split()[0], "zendriver from", zendriver.__file__)

T0 = time.monotonic()


def ts():
    return f"{time.monotonic() - T0:6.3f}s"


SERVER_LOG = []
DROP = set()
DELAY = {}


async def handler(ws):
    async for raw in ws:
        msg = json.loads(raw)
        SERVER_LOG.append((ts(), msg["method"]))
        print(f"  [peer {ts()}] got {msg['method']} id={msg['id']}")
        if msg["method"] in DROP:
            continue  # never answer
        if msg["method"] in DELAY:
            async def later(m=msg):
                await asyncio.sleep(DELAY[m["method"]])
                print(f"  [peer {ts()}] late reply to {m['method']} id={m['id']}")
                await ws.send(json.dumps({"id": m["id"], "result": {}}))
            asyncio.create_task(later())
            continue
        if msg["method"] == "Runtime.evaluate":
            result = {"result": {"type": "number", "value": 42, "description": "42"}}
        else:
            result = {}
        await ws.send(json.dumps({"id": msg["id"], "result": result}))


def coro_chain(task):
    """walk the cr_await chain to show exactly where a task is suspended"""
    out = []
    c = task.get_coro()
    while c is not None:
        f = getattr(c, "cr_frame", None) or getattr(c, "gi_frame", None)
        if f is None:
            break
        out.append(f"{f.f_code.co_filename.split('/zendriver/')[-1]}:{f.f_lineno} in {f.f_code.co_name}")
        c = getattr(c, "cr_await", None) or getattr(c, "gi_yieldfrom", None)
    return out


async def new_conn(url, with_handler):
    conn = Connection(url)
    if with_handler:
        conn.add_handler(cdp.network.RequestWillBeSent, lambda ev: None)
    return conn


async def scenario(name, url, drop, with_handler, mode, timeout=1.0, delay=None):
    global T0
    T0 = time.monotonic()
    DROP.clear()
    DROP.update(drop)
    SERVER_LOG.clear()
    DELAY.clear()
    DELAY.update(delay or {})
    print(f"\n=== {name}: drop={sorted(drop)} handler={with_handler} mode={mode} timeout={timeout}")
    conn = await new_conn(url, with_handler)
    task = None
    try:
        if mode == "wait_for":
            # inner wait_for is the code-under-test's caller; outer asyncio.wait is the safety net
            task = asyncio.create_task(
                asyncio.wait_for(conn.send(cdp.runtime.evaluate("6*7")), timeout)
            )
            done, _ = await asyncio.wait({task}, timeout=timeout + 4)
        else:  # task.cancel()
            task = asyncio.create_task(conn.send(cdp.runtime.evaluate("6*7")))
            await asyncio.sleep(timeout)
            print(f"  [{ts()}] task.cancel() -> {task.cancel()}")
            done, _ = await asyncio.wait({task}, timeout=4)
        if not done:
            print(f"  [{ts()}] RESULT: STILL RUNNING {timeout + 4 if mode=='wait_for' else 4}s after start/cancel (HANG)")
            print("  task.print_stack():")
            task.print_stack(file=sys.stdout)
            print("  cr_await chain:")
            for line in coro_chain(task):
                print("     ", line)
            print("  task.cancelling() =", task.cancelling())
            task.cancel()  # second cancel, cleanup
            try:
                await asyncio.wait_for(task, 3)
            except BaseException as e:
                print(f"  cleanup: second cancel -> {type(e).__name__}")
        elif task.cancelled():
            print(f"  [{ts()}] RESULT: task cancelled (CancelledError propagated) -- correct")
        elif task.exception() is not None:
            print(f"  [{ts()}] RESULT: raised {type(task.exception()).__name__} -- correct")
        else:
            print(f"  [{ts()}] RESULT: returned normally {task.result()!r} -- cancel/timeout IGNORED")
        print("  peer saw:", SERVER_LOG)
    finally:
        if conn.listener:
            conn.listener.cancel()
        if conn.websocket is not None:
            await conn.websocket.close()


async def main():
    async with serve(handler, "127.0.0.1", 0) as server:
        port = server.sockets[0].getsockname()[1]
        url = f"ws://127.0.0.1:{port}"
        # controls: no handler -> no nested Domain.enable
        if len(sys.argv) > 1 and sys.argv[1] == "delay":
            await scenario("BUG-5 slow Network.enable (2s), timeout 1s", url, set(), True, "wait_for", delay={"Network.enable": 2.0})
            await scenario("BUG-6 slow Network.enable (2s), cancel at 1s", url, set(), True, "cancel", delay={"Network.enable": 2.0})
            await scenario("CONTROL-C slow evaluate (2s), no handler, timeout 1s", url, set(), False, "wait_for", delay={"Runtime.evaluate": 2.0})
            return
        await scenario("CONTROL-A", url, {"Runtime.evaluate"}, False, "wait_for")
        await scenario("CONTROL-B", url, {"Runtime.evaluate"}, False, "cancel")
        # bug: nested Network.enable never answered
        await scenario("BUG-1 timeout ignored, cmd answered", url, {"Network.enable"}, True, "wait_for")
        await scenario("BUG-2 timeout ignored, cmd unanswered", url, {"Network.enable", "Runtime.evaluate"}, True, "wait_for")
        await scenario("BUG-3 cancel ignored, cmd answered", url, {"Network.enable"}, True, "cancel")
        await scenario("BUG-4 cancel ignored, cmd unanswered", url, {"Network.enable", "Runtime.evaluate"}, True, "cancel")


asyncio.run(asyncio.wait_for(main(), 100))
