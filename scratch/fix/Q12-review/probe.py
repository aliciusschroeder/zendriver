"""browser-free probes for the Q12 fix (Connection._register_handlers cancellation)"""

import asyncio
import gc
import json
import logging
import sys
from typing import Any

import websockets

import zendriver as zd
from zendriver.core.connection import Connection

print(sys.version.split()[0], zd.__file__)

asyncio_errors: list[str] = []


class Fake:
    """answers everything except methods in ``stall``; methods in ``fail_once`` get one error"""

    def __init__(self, stall: set[str], fail_once: set[str] | None = None) -> None:
        self.closed = False
        self.q: asyncio.Queue[str] = asyncio.Queue()
        self.stall = stall
        self.fail_once = set(fail_once or ())
        self.delivered: list[str] = []
        self.stalled = asyncio.Event()

    async def send(self, message: str) -> None:
        m = json.loads(message)
        self.delivered.append(m["method"])
        if m["method"] in self.fail_once:
            self.fail_once.discard(m["method"])
            self.q.put_nowait(
                json.dumps({"id": m["id"], "error": {"code": -1, "message": "nope"}})
            )
            return
        if m["method"] in self.stall:
            self.stalled.set()
            return
        self.q.put_nowait(json.dumps({"id": m["id"], "result": {}}))

    async def recv(self) -> str:
        return await self.q.get()

    async def close(self) -> None:
        self.closed = True


def make(ws: Fake) -> Connection:
    async def connect(*a: Any, **k: Any) -> Fake:
        return ws

    websockets.connect = connect  # type: ignore[assignment]
    return Connection("ws://fake/devtools/browser/fake")


async def finish(conn: Connection, task: "asyncio.Task[Any]") -> None:
    await conn.aclose()
    for _ in range(3):
        if task.done():
            break
        task.cancel()
        await asyncio.wait({task}, timeout=1)
    if task.done() and not task.cancelled():
        task.exception()


async def probe_outer_tx_leak() -> None:
    """cancel lands in send()'s own _register_handlers: is the never-sent outer tx left in mapper?"""
    ws = Fake(stall={"Network.enable"}, fail_once={"Network.enable"})
    conn = make(ws)
    conn.add_handler(zd.cdp.network.RequestWillBeSent, lambda e: None)
    task = asyncio.create_task(conn.send(zd.cdp.target.set_discover_targets(True)))
    await asyncio.wait_for(ws.stalled.wait(), 5)
    task.cancel()
    await asyncio.wait({task}, timeout=3)
    pending = {
        i: (tx.method, tx.done()) for i, tx in conn.mapper.items() if not tx.done()
    }
    print(
        "[outer-tx-leak] done=%s cancelled=%s delivered=%s pending-not-done=%s"
        % (task.done(), task.done() and task.cancelled(), ws.delivered, pending)
    )
    await finish(conn, task)
    del task
    gc.collect()
    await asyncio.sleep(0)


async def probe_nested_two_domains() -> None:
    """two handler domains; cancel during the second (nested) enable"""
    ws = Fake(stall={"Runtime.enable"})
    conn = make(ws)
    conn.add_handler(zd.cdp.network.RequestWillBeSent, lambda e: None)
    conn.add_handler(zd.cdp.runtime.ConsoleAPICalled, lambda e: None)
    task = asyncio.create_task(conn.send(zd.cdp.target.set_discover_targets(True)))
    await asyncio.wait_for(ws.stalled.wait(), 5)
    task.cancel()
    await asyncio.wait({task}, timeout=3)
    print(
        "[nested] cancelled=%s delivered=%s enabled=%s"
        % (
            task.done() and task.cancelled(),
            ws.delivered,
            [d.__name__ for d in conn.enabled_domains],
        )
    )
    ws.stall = set()
    ws.delivered.clear()
    await asyncio.wait_for(conn.send(zd.cdp.target.set_discover_targets(True)), 3)
    print(
        "[nested] next send delivered=%s enabled=%s"
        % (ws.delivered, [d.__name__ for d in conn.enabled_domains])
    )
    await finish(conn, task)


async def probe_manual_enable_race() -> None:
    """auto enable pending, user manually enables same domain, then auto enable is cancelled"""
    ws = Fake(stall={"Network.enable"})
    conn = make(ws)
    conn.add_handler(zd.cdp.network.RequestWillBeSent, lambda e: None)
    a = asyncio.create_task(conn.send(zd.cdp.target.set_discover_targets(True)))
    await asyncio.wait_for(ws.stalled.wait(), 5)
    conn._update_manual_domain("Network", "enable")
    a.cancel()
    await asyncio.wait({a}, timeout=3)
    exc = None if not a.done() or a.cancelled() else a.exception()
    print(
        "[manual-race] cancelled=%s exc=%r enabled=%s manual=%s"
        % (
            a.done() and a.cancelled(),
            exc,
            [d.__name__ for d in conn.enabled_domains],
            [d.__name__ for d in conn.manually_enabled_domains],
        )
    )
    await finish(conn, a)


async def probe_concurrent_sharer() -> None:
    """B piggybacks on A's pending enable; A is cancelled; B and a later C still work"""
    ws = Fake(stall={"Network.enable"})
    conn = make(ws)
    conn.add_handler(zd.cdp.network.RequestWillBeSent, lambda e: None)
    a = asyncio.create_task(conn.send(zd.cdp.target.set_discover_targets(True)))
    await asyncio.wait_for(ws.stalled.wait(), 5)
    b = asyncio.create_task(conn.send(zd.cdp.target.set_discover_targets(False)))
    await asyncio.sleep(0.1)
    a.cancel()
    await asyncio.wait({a, b}, timeout=3)
    print(
        "[sharer] a.cancelled=%s b.done=%s b.exc=%r delivered=%s"
        % (
            a.done() and a.cancelled(),
            b.done(),
            (b.exception() if b.done() and not b.cancelled() else None),
            ws.delivered,
        )
    )
    ws.stall = set()
    ws.delivered.clear()
    await asyncio.wait_for(conn.send(zd.cdp.target.set_discover_targets(True)), 3)
    print("[sharer] next send delivered=%s" % ws.delivered)
    await finish(conn, a)
    await finish(conn, b)


async def main() -> None:
    loop = asyncio.get_running_loop()

    def handler(loop: Any, ctx: dict[str, Any]) -> None:
        asyncio_errors.append(ctx.get("message", ""))

    loop.set_exception_handler(handler)
    for probe in (
        probe_outer_tx_leak,
        probe_nested_two_domains,
        probe_manual_enable_race,
        probe_concurrent_sharer,
    ):
        try:
            await asyncio.wait_for(probe(), 20)
        except BaseException as e:
            print("PROBE", probe.__name__, "raised", repr(e))
        gc.collect()
        await asyncio.sleep(0.1)
        print("  asyncio exception-handler messages after", probe.__name__, asyncio_errors)
        asyncio_errors.clear()


logging.basicConfig(level=logging.WARNING)
asyncio.run(main())
