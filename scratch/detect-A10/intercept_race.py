import asyncio, json, sys
import websockets
from zendriver import cdp
from zendriver.core.connection import Connection
from zendriver.core.expect import RequestExpectation
from zendriver.core.intercept import BaseFetchInterception
from expect_race import rwbs, paused
DELAY = float(sys.argv[1])
received = []
async def handler(ws):
    async for raw in ws:
        msg = json.loads(raw); p = msg.get("params"); received.append((msg["method"], p.get("requestId") if isinstance(p, dict) else None))
        await ws.send(json.dumps({"id": msg["id"], "result": {}}))
        if msg["method"] == "Network.enable":
            await ws.send(json.dumps(rwbs("R1", "http://x/a.png")))
            await ws.send(json.dumps(rwbs("R2", "http://x/b.png")))
        if msg["method"] == "Fetch.enable":
            if DELAY: await asyncio.sleep(DELAY)
            await ws.send(json.dumps(paused("P1", "http://x/a.png")))
            await ws.send(json.dumps(paused("P2", "http://x/b.png")))

async def main():
    errors = []
    loop = asyncio.get_running_loop()
    loop.set_exception_handler(lambda l, ctx: errors.append(repr(ctx.get("exception"))))
    async with websockets.serve(handler, "127.0.0.1", 0) as server:
        port = server.sockets[0].getsockname()[1]
        conn = Connection(f"ws://127.0.0.1:{port}/devtools/page/X")
        exp = RequestExpectation(conn, r".*\.png")
        async with exp:
            await conn.send(cdp.page.bring_to_front())
            ev = await asyncio.wait_for(exp.value, 5)
            await asyncio.sleep(0.3)
            print("request_future.request_id =", ev.request_id, " exp.request_id =", exp.request_id)
        del exp
        icp = BaseFetchInterception(conn, "*.png", cdp.fetch.RequestStage.REQUEST, cdp.network.ResourceType.IMAGE)
        async with icp:
            try:
                ev = await asyncio.wait_for(icp.response_future, 3)
                await icp.continue_request()
                print("intercepted", ev.request_id)
            except TimeoutError:
                print("interception: response_future never resolved within 3s (RequestPaused dropped); handlers now:", dict(conn.handlers))
            await asyncio.sleep(0.3)
        import gc; gc.collect(); await asyncio.sleep(0.1)
        print("loop exceptions:", errors)
        print("server saw:", received)
        await conn.aclose()
asyncio.run(asyncio.wait_for(main(), 30))
