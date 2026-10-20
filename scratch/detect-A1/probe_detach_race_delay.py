"""Probe: a session response that arrives in the same burst as Target.detachedFromTarget
is discarded and the caller gets 'target session was detached'."""
import asyncio
import json

import websockets

import zendriver as zd
from zendriver.core.connection import Connection, ProtocolException

TARGET = "T1"
SESSION = "S1"


COUNTER = [0]


async def handler(ws):
    async for raw in ws:
        msg = json.loads(raw)
        m = msg["method"]
        if m == "Target.attachToTarget":
            COUNTER[0] += 1
            await ws.send(json.dumps({"id": msg["id"], "result": {"sessionId": f"S{COUNTER[0]}"}}))
        elif m == "Runtime.evaluate" and msg.get("sessionId"):
            sid = msg["sessionId"]
            # reply, then the target goes away (e.g. the script closed the page)
            await ws.send(json.dumps({"id": msg["id"], "sessionId": sid,
                                      "result": {"result": {"type": "number", "value": 2, "description": "2"}}}))
            await asyncio.sleep(0.05)
            await ws.send(json.dumps({"method": "Target.detachedFromTarget",
                                      "params": {"sessionId": sid, "targetId": TARGET}}))
        else:
            reply = {"id": msg["id"], "result": {}}
            if "sessionId" in msg:
                reply["sessionId"] = msg["sessionId"]
            await ws.send(json.dumps(reply))


class Owner:
    config = None
    _headless_user_agent = None

    def __init__(self, url):
        self.connection = Connection(url, _owner=self)


async def main():
    server = await websockets.serve(handler, "127.0.0.1", 0)
    url = f"ws://127.0.0.1:{server.sockets[0].getsockname()[1]}/devtools/browser/x"
    owner = Owner(url)
    info = zd.cdp.target.TargetInfo(target_id=zd.cdp.target.TargetID(TARGET), type_="page", title="", url="about:blank",
                                    attached=False, can_access_opener=False)
    tab = Connection(url.replace("browser/x", "page/T1"), target=info, _owner=owner)
    ok = bad = 0
    for i in range(20):
        try:
            await asyncio.wait_for(tab.send(zd.cdp.runtime.evaluate("1+1")), 5)
            ok += 1
        except ProtocolException as e:
            bad += 1
            last = str(e).splitlines()[0]
        await asyncio.sleep(0.2)
    print(f"evaluate replied successfully by chrome: 20; caller saw success: {ok}, saw ProtocolException: {bad}")
    if bad:
        print("example error:", last)
    await owner.connection.aclose()
    server.close()


asyncio.run(main())
