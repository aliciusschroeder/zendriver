import asyncio, json, sys, types
import websockets
from zendriver import cdp
from zendriver.core.connection import Connection, ProtocolException

DELAY = float(sys.argv[1])  # delay between attach reply and detachedFromTarget

async def handler(ws):
    async for raw in ws:
        m = json.loads(raw)
        if m.get("sessionId") is not None:
            # like chrome (verified): reply for an unknown session carries no sessionId
            await ws.send(json.dumps({"id": m["id"], "error": {"code": -32001, "message": "Session with given id not found."}}))
            continue
        if m["method"] == "Target.attachToTarget":
            await ws.send(json.dumps({"id": m["id"], "result": {"sessionId": "S1"}}))
            if DELAY: await asyncio.sleep(DELAY)
            # the target goes away right after the attach
            await ws.send(json.dumps({"method": "Target.detachedFromTarget", "params": {"sessionId": "S1", "targetId": "T1"}}))
        else:
            await ws.send(json.dumps({"id": m["id"], "result": {}}))

async def main():
    async with websockets.serve(handler, "127.0.0.1", 0) as srv:
        port = srv.sockets[0].getsockname()[1]
        url = f"ws://127.0.0.1:{port}"
        browser_conn = Connection(url)
        owner = types.SimpleNamespace(connection=browser_conn, config=None)
        target = cdp.target.TargetInfo(target_id=cdp.target.TargetID("T1"), type_="page", title="", url="about:blank", attached=False, can_access_opener=False)
        tab = Connection(url, target=target, _owner=owner)
        try:
            r = await asyncio.wait_for(tab.send(cdp.runtime.evaluate("1")), 3)
            print(f"delay={DELAY}: returned {r}")
        except ProtocolException as e:
            print(f"delay={DELAY}: ProtocolException: {str(e).splitlines()[0]}")
        except asyncio.TimeoutError:
            print(f"delay={DELAY}: HANG - send never completed; session_id={tab.session_id} registered={list(browser_conn._sessions)} browser mapper={list(browser_conn.mapper)} tab mapper={list(tab.mapper)}")
        # every later send hangs too
        try:
            await asyncio.wait_for(tab.send(cdp.runtime.evaluate("2")), 2)
        except asyncio.TimeoutError:
            print("   second send also HANGS")
        except ProtocolException as e:
            print("   second send: ProtocolException", str(e).splitlines()[0])
        await browser_conn.aclose()

asyncio.run(asyncio.wait_for(main(), 30))
