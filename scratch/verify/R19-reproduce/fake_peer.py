"""Fake CDP peer reproducer for R19: sync handler + feed_cdp, and lambda returning coroutine."""
import asyncio, json, sys, threading, warnings, gc
import websockets
import zendriver
from zendriver import cdp
from zendriver.core.connection import Connection

print("zendriver from", zendriver.__file__, "python", sys.version.split()[0], "websockets", websockets.__version__)

PAUSED = {
    "method": "Fetch.requestPaused",
    "params": {
        "requestId": "interception-1",
        "request": {"url": "http://x/", "method": "GET", "headers": {}, "initialPriority": "High", "referrerPolicy": "no-referrer"},
        "frameId": "F1",
        "resourceType": "Document",
    },
}
CONSOLE = {
    "method": "Runtime.consoleAPICalled",
    "params": {"type": "log", "args": [], "executionContextId": 1, "timestamp": 1.0},
}

async def run(kind: str) -> None:
    received: list[str] = []
    got_continue = asyncio.Event()
    loop_errors: list[str] = []
    loop = asyncio.get_running_loop()
    loop.set_exception_handler(lambda l, ctx: loop_errors.append(repr(ctx.get("exception")) + " | " + ctx.get("message", "")))

    async def handler(ws):
        async for raw in ws:
            msg = json.loads(raw)
            received.append(msg["method"])
            await ws.send(json.dumps({"id": msg["id"], "result": {}}))
            if msg["method"] == "Fetch.enable":
                await ws.send(json.dumps(PAUSED))
            if msg["method"] == "Runtime.enable":
                await ws.send(json.dumps(CONSOLE))
            if msg["method"] == "Fetch.continueRequest":
                got_continue.set()

    async with websockets.serve(handler, "127.0.0.1", 0) as server:
        port = server.sockets[0].getsockname()[1]
        conn = Connection(f"ws://127.0.0.1:{port}/devtools/page/X")
        threads = []
        if kind in ("sync", "sync-conn", "async"):
            if kind == "sync":
                def on_paused(ev):
                    threads.append(threading.current_thread().name)
                    try:
                        conn.feed_cdp(cdp.fetch.continue_request(request_id=ev.request_id))
                    except Exception as e:
                        print("  feed_cdp raised inside handler:", type(e).__name__, e)
                        raise
            elif kind == "sync-conn":
                # the exact B14.4/A12.3 form: lambda accepting (event, connection)
                def on_paused(ev, c):  # noqa
                    threads.append(threading.current_thread().name)
                    c.feed_cdp(cdp.fetch.continue_request(request_id=ev.request_id))
                on_paused_l = lambda ev, c: (threads.append(threading.current_thread().name), c.feed_cdp(cdp.fetch.continue_request(request_id=ev.request_id)))
                on_paused = on_paused_l
            else:
                async def on_paused(ev):
                    threads.append(threading.current_thread().name)
                    conn.feed_cdp(cdp.fetch.continue_request(request_id=ev.request_id))
            conn.add_handler(cdp.fetch.RequestPaused, on_paused)
            await conn.send(cdp.fetch.enable())
            try:
                await asyncio.wait_for(got_continue.wait(), 3)
                print(f"  kind={kind}: Fetch.continueRequest RECEIVED by peer; handler thread={threads}")
            except asyncio.TimeoutError:
                print(f"  kind={kind}: Fetch.continueRequest NEVER sent within 3s (request stays paused); handler thread={threads}; peer saw={received}")
        else:
            ran = []
            async def process(e):
                ran.append(e)
            if kind == "lambda-coro":
                cb = lambda e: process(e)
            elif kind == "lambda-task":
                cb = lambda e: asyncio.create_task(process(e))
            elif kind == "async-call-obj":
                class H:
                    async def __call__(self, e):
                        ran.append(e)
                cb = H()
            import inspect
            print(f"  kind={kind}: inspect.iscoroutinefunction(cb)={inspect.iscoroutinefunction(cb)}")
            conn.add_handler(cdp.runtime.ConsoleAPICalled, cb)
            await conn.send(cdp.runtime.enable())
            await asyncio.sleep(1.0)
            gc.collect()
            await asyncio.sleep(0.1)
            print(f"  kind={kind}: async work ran {len(ran)} time(s) (expected 1)")
        await conn.aclose() if hasattr(conn, "aclose") else None
        await asyncio.sleep(0.2)
    gc.collect()
    await asyncio.sleep(0.05)
    for e in loop_errors:
        print("  loop error:", e)

async def main():
    warnings.simplefilter("always")
    for kind in sys.argv[1:] or ["async", "sync", "sync-conn", "lambda-coro", "lambda-task", "async-call-obj"]:
        print(f"== {kind}")
        await asyncio.wait_for(run(kind), 30)

asyncio.run(main())
