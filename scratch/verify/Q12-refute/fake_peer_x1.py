"""Browser-free probe for SEED-X1: cancellation landing in the nested
Domain.enable inside Connection._register_handlers.

Fake CDP peer: answers every command except the methods in DROP.
"""
import asyncio
import json
import sys
import time

import websockets
from stackwalk import coro_chain
from websockets.asyncio.server import serve

import zendriver
from zendriver import cdp
from zendriver.core.connection import Connection

print("zendriver from", zendriver.__file__, "python", sys.version.split()[0])

DROP: set[str] = set()
SEEN: list[str] = []


async def handler(ws):
    async for raw in ws:
        msg = json.loads(raw)
        SEEN.append(msg["method"])
        if msg["method"] in DROP:
            continue
        result = {}
        if msg["method"] == "Runtime.evaluate":
            result = {"result": {"type": "number", "value": 2}}
        await ws.send(json.dumps({"id": msg["id"], "result": result}))


async def scenario(name, url, add_handler, drop, inner_timeout=1.0, net=6.0, mode="wait_for"):
    DROP.clear()
    DROP.update(drop)
    SEEN.clear()
    conn = Connection(url)
    await conn.aopen()
    if add_handler:
        conn.add_handler(cdp.network.RequestWillBeSent, lambda e: None)

    async def call():
        if mode == "wait_for":
            return await asyncio.wait_for(
                conn.send(cdp.runtime.evaluate("1+1")), inner_timeout
            )
        return await conn.send(cdp.runtime.evaluate("1+1"))

    t0 = time.monotonic()
    task = asyncio.create_task(call())
    if mode == "cancel":
        await asyncio.sleep(inner_timeout)
        task.cancel()
    done, _ = await asyncio.wait({task}, timeout=net)
    dt = time.monotonic() - t0
    if not done:
        print(f"[{name}] HUNG: still running after {dt:.1f}s (inner timeout {inner_timeout}s); sent={SEEN}")
        print("   chain:", " -> ".join(coro_chain(task)))
        task.cancel()
        try:
            await asyncio.wait_for(task, 2)
        except BaseException as e:
            print(f"[{name}] second cancel -> {type(e).__name__}")
    else:
        try:
            r = task.result()
            print(f"[{name}] returned {r!r} after {dt:.2f}s (NO TimeoutError/CancelledError); sent={SEEN}")
        except BaseException as e:
            print(f"[{name}] raised {type(e).__name__} after {dt:.2f}s; sent={SEEN}")
    print(f"   enabled_domains={[m.__name__ for m in conn.enabled_domains]}")
    await conn.aclose()


async def main():
    async with serve(handler, "127.0.0.1", 0) as server:
        port = server.sockets[0].getsockname()[1]
        url = f"ws://127.0.0.1:{port}"
        # control: no handler, Runtime.evaluate never answered -> TimeoutError at 1s
        await scenario("control-no-handler", url, False, {"Runtime.evaluate"})
        # bug A: handler present, Network.enable + Runtime.evaluate never answered
        await scenario("handler+both-dropped", url, True, {"Network.enable", "Runtime.evaluate"})
        # bug B: Network.enable never answered, evaluate answered -> timeout silently ignored
        await scenario("handler+enable-dropped", url, True, {"Network.enable"})
        # bug C: task.cancel() instead of wait_for
        await scenario("cancel+both-dropped", url, True, {"Network.enable", "Runtime.evaluate"}, mode="cancel")
        # control 2: handler present, only evaluate dropped (enable answered) -> TimeoutError
        await scenario("handler+eval-dropped", url, True, {"Runtime.evaluate"})


asyncio.run(main())
