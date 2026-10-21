"""a bounded call on a flat-session tab is cut off while Target.attachToTarget is pending."""
import asyncio, json, sys, types
import websockets
import zendriver as zd
from zendriver import cdp
from zendriver.core.connection import Connection


class Peer:
    def __init__(self):
        self.frames = asyncio.Queue(); self.closed = False; self.methods = []
        self.held = []; self.n_attach = 0

    async def send(self, message):
        cmd = json.loads(message); self.methods.append(cmd["method"])
        result = {}
        if cmd["method"] == "Target.attachToTarget":
            self.n_attach += 1
            result = {"sessionId": f"S{self.n_attach}"}
            if self.n_attach == 1:          # first attach answered late
                self.held.append({"id": cmd["id"], "result": result}); return
        reply = {"id": cmd["id"], "result": result}
        if "sessionId" in cmd: reply["sessionId"] = cmd["sessionId"]
        self.frames.put_nowait(reply)

    async def recv(self):
        return json.dumps(await self.frames.get())

    async def close(self):
        self.closed = True


async def main():
    print("python", sys.version.split()[0], zd.__file__)
    peer = Peer()
    async def connect(*a, **k): return peer
    websockets.connect = connect
    browser_conn = Connection("ws://fake/devtools/browser/B")
    owner = types.SimpleNamespace(connection=browser_conn, config=None)
    tab = Connection("ws://fake/devtools/page/T1", target=cdp.target.TargetInfo(
        target_id=cdp.target.TargetID("T1"), type_="page", title="", url="about:blank",
        attached=False, can_access_opener=False), _owner=owner)
    try:
        try:
            await asyncio.wait_for(tab.send(cdp.page.bring_to_front()), 0.3)
        except asyncio.TimeoutError:
            print("first call: TimeoutError")
        print("attach_lock locked:", tab._attach_lock.locked(), "session_id:", tab.session_id,
              "browser mapper:", {k: (v.method, v.cancelled()) for k, v in browser_conn.mapper.items()})
        # the late answer arrives
        for r in peer.held: peer.frames.put_nowait(r)
        await asyncio.sleep(0.2)
        r = await asyncio.wait_for(tab.send(cdp.page.bring_to_front()), 3)
        print("second call OK; session_id:", tab.session_id, "attaches sent:", peer.n_attach,
              "browser mapper:", browser_conn.mapper, "sessions:", list(browser_conn._sessions))
    finally:
        await tab.aclose(); await browser_conn.aclose()

asyncio.run(main())
