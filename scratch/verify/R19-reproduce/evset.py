import asyncio, json, sys, time, websockets, threading
from zendriver import cdp
from zendriver.core.connection import Connection
CONSOLE = {"method": "Runtime.consoleAPICalled", "params": {"type": "log", "args": [], "executionContextId": 1, "timestamp": 1.0}}
async def main():
    debug = asyncio.get_running_loop().get_debug()
    errs = []
    asyncio.get_running_loop().set_exception_handler(lambda l, c: errs.append(repr(c.get("exception"))))
    async def handler(ws):
        async for raw in ws:
            msg = json.loads(raw)
            await ws.send(json.dumps({"id": msg["id"], "result": {}}))
            if msg["method"] == "Runtime.enable":
                await asyncio.sleep(0.5)
                await ws.send(json.dumps(CONSOLE))
    async with websockets.serve(handler, "127.0.0.1", 0) as server:
        port = server.sockets[0].getsockname()[1]
        conn = Connection(f"ws://127.0.0.1:{port}/devtools/page/X")
        flag = asyncio.Event()
        t = {}
        def cb(e):
            t["set"] = time.monotonic()
            flag.set()
        conn.add_handler(cdp.runtime.ConsoleAPICalled, cb)
        await conn.send(cdp.runtime.enable())
        try:
            await asyncio.wait_for(flag.wait(), 3)
            print(f"debug={debug}: Event.set from handler thread woke waiter after {1000*(time.monotonic()-t['set']):.1f} ms")
        except asyncio.TimeoutError:
            print(f"debug={debug}: waiter never woke; errors={errs}")
        await asyncio.sleep(0.2)
    print("errors:", errs)
asyncio.run(asyncio.wait_for(main(), 20), debug=len(sys.argv) > 1)
