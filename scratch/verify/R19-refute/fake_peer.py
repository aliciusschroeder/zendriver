import asyncio, gc, json, sys
import websockets
from websockets.asyncio.server import serve
import zendriver
from zendriver import cdp
from zendriver.core.connection import Connection
print("zendriver from", zendriver.__file__, "python", sys.version.split()[0], flush=True)
EV = {"method": "Fetch.requestPaused", "params": {"requestId": "r1", "request": {"url": "http://x/", "method": "GET", "headers": {}, "initialPriority": "High", "referrerPolicy": "no-referrer"}, "frameId": "f", "resourceType": "Document"}}
async def main(kind):
    got = []
    async def h(ws):
        async for raw in ws:
            m = json.loads(raw); got.append(m["method"])
            await ws.send(json.dumps({"id": m["id"], "result": {}}))
            if m["method"] == "Fetch.enable":
                await ws.send(json.dumps(EV))
    async with serve(h, "127.0.0.1", 0) as srv:
        port = srv.sockets[0].getsockname()[1]
        conn = Connection(f"ws://127.0.0.1:{port}")
        if kind == "sync":
            conn.add_handler(cdp.fetch.RequestPaused, lambda ev, c: c.feed_cdp(cdp.fetch.continue_request(request_id=ev.request_id)))
        else:
            async def a(ev, c): c.feed_cdp(cdp.fetch.continue_request(request_id=ev.request_id))
            conn.add_handler(cdp.fetch.RequestPaused, a)
        await asyncio.wait_for(conn.send(cdp.fetch.enable()), 5)
        await asyncio.sleep(1); gc.collect(); await asyncio.sleep(0.1)
        print(f"[{kind}] methods received by peer: {got}", flush=True)
        await conn.aclose()
asyncio.run(main(sys.argv[1]))
