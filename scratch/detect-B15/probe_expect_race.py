import asyncio, json, logging, sys
import websockets
from zendriver import cdp
from zendriver.core.connection import Connection
from zendriver.core.expect import ResponseExpectation

def rwbs(rid, url):
    return {"method": "Network.requestWillBeSent", "params": {
        "requestId": rid, "loaderId": "L", "documentURL": "http://x/", "request": {
            "url": url, "method": "GET", "headers": {}, "initialPriority": "High",
            "referrerPolicy": "no-referrer"}, "timestamp": 1.0, "wallTime": 1.0,
        "initiator": {"type": "other"}, "redirectHasExtraInfo": False, "type": "Fetch"}}

def resp(rid, url):
    return {"method": "Network.responseReceived", "params": {
        "requestId": rid, "loaderId": "L", "timestamp": 1.0, "type": "Fetch",
        "hasExtraInfo": False, "response": {"url": url, "status": 200, "statusText": "OK",
        "headers": {}, "mimeType": "application/json", "charset": "", "connectionReused": False,
        "connectionId": 1, "encodedDataLength": 1, "securityState": "secure"}}}

async def handler(ws):
    async for raw in ws:
        msg = json.loads(raw)
        await ws.send(json.dumps({"id": msg["id"], "result": {}}))
        if msg["method"] == "Runtime.runIfWaitingForDebugger":
            # page fires two fetches matching the pattern at the same time
            for m in (rwbs("R1", "http://x/a.json"), rwbs("R2", "http://x/b.json"),
                      resp("R1", "http://x/a.json"), resp("R2", "http://x/b.json")):
                await ws.send(json.dumps(m))

async def main():
    print(sys.version.split()[0])
    errors = []
    asyncio.get_running_loop().set_exception_handler(lambda l, c: errors.append(repr(c.get("exception"))))
    async with websockets.serve(handler, "127.0.0.1", 0) as server:
        port = server.sockets[0].getsockname()[1]
        conn = Connection(f"ws://127.0.0.1:{port}")
        async with ResponseExpectation(conn, r"http://x/.*\.json") as exp:
            await conn.send(cdp.runtime.run_if_waiting_for_debugger())
            req = await asyncio.wait_for(exp.request, 3)
            res = await asyncio.wait_for(exp.response, 3)
            print("expectation .request url :", req.url)
            print("expectation .response url:", res.url, "| request_id:", exp.request_id)
        await conn.aclose()
    import gc; gc.collect(); await asyncio.sleep(0.1)
    print("unhandled task errors:", errors)

asyncio.run(main())
