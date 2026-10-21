"""Minimal fake CDP peer for R22 reproductions (written from scratch by the R22 reproduce verifier).

Behaviour knobs (all set on the FakePeer instance):
  detach_after_attach: None -> never; float -> seconds to wait after the attach reply
                       before sending Target.detachedFromTarget for the new session
                       (0.0 means "same burst": no yield between the two websocket sends)
  detach_after_method: method name; when a session command with this method arrives the
                       peer answers it (with sessionId) and then sends detachedFromTarget
  detach_after_method_delay: seconds between that reply and the detach (0.0 = same burst)
Commands that carry a sessionId the peer does not consider alive are answered the way
Chrome does it: {"id": N, "error": {"code": -32001, "message": "Session with given id not found."}}
with NO sessionId field.
"""

import asyncio
import json
import itertools

import websockets
from websockets.asyncio.server import serve


class FakePeer:
    def __init__(self):
        self.detach_after_attach = None
        self.detach_after_method = None
        self.detach_after_method_delay = 0.0
        self.alive_sessions = set()
        self.attached_log = []
        self.received = []
        self._sid = itertools.count(1)
        self.server = None
        self.url = None
        self.sent_frames = []

    async def start(self):
        self.server = await serve(self._handler, "127.0.0.1", 0)
        port = self.server.sockets[0].getsockname()[1]
        self.url = f"ws://127.0.0.1:{port}/devtools/browser/fake"
        return self

    async def stop(self):
        self.server.close()
        await self.server.wait_closed()

    async def _send(self, ws, obj):
        self.sent_frames.append(obj)
        await ws.send(json.dumps(obj))

    async def _detach_later(self, ws, sid, delay):
        await asyncio.sleep(delay)
        self.alive_sessions.discard(sid)
        await self._send(
            ws,
            {
                "method": "Target.detachedFromTarget",
                "params": {"sessionId": sid, "targetId": "T1"},
            },
        )

    async def _handler(self, ws):
        try:
            async for raw in ws:
                msg = json.loads(raw)
                self.received.append(msg)
                mid = msg["id"]
                method = msg["method"]
                sid = msg.get("sessionId")
                if sid is not None:
                    if sid not in self.alive_sessions:
                        # what real chrome does: error reply WITHOUT a sessionId
                        await self._send(
                            ws,
                            {
                                "id": mid,
                                "error": {
                                    "code": -32001,
                                    "message": "Session with given id not found.",
                                },
                            },
                        )
                        continue
                    if method == "Runtime.evaluate":
                        result = {"result": {"type": "number", "value": 2, "description": "2"}}
                    else:
                        result = {}
                    await self._send(ws, {"id": mid, "sessionId": sid, "result": result})
                    if method == self.detach_after_method:
                        if self.detach_after_method_delay == 0.0:
                            # same burst: no yield between the two writes
                            self.alive_sessions.discard(sid)
                            await self._send(
                                ws,
                                {
                                    "method": "Target.detachedFromTarget",
                                    "params": {"sessionId": sid, "targetId": "T1"},
                                },
                            )
                        else:
                            asyncio.create_task(
                                self._detach_later(ws, sid, self.detach_after_method_delay)
                            )
                    continue
                # browser level commands
                if method == "Target.attachToTarget":
                    new_sid = f"S{next(self._sid)}"
                    self.alive_sessions.add(new_sid)
                    self.attached_log.append(new_sid)
                    await self._send(ws, {"id": mid, "result": {"sessionId": new_sid}})
                    if self.detach_after_attach is not None:
                        if self.detach_after_attach == 0.0:
                            self.alive_sessions.discard(new_sid)
                            await self._send(
                                ws,
                                {
                                    "method": "Target.detachedFromTarget",
                                    "params": {"sessionId": new_sid, "targetId": "T1"},
                                },
                            )
                        else:
                            asyncio.create_task(
                                self._detach_later(ws, new_sid, self.detach_after_attach)
                            )
                    continue
                if method == "Target.detachFromTarget":
                    s = msg.get("params", {}).get("sessionId")
                    self.alive_sessions.discard(s)
                    await self._send(ws, {"id": mid, "result": {}})
                    continue
                await self._send(ws, {"id": mid, "result": {}})
        except websockets.exceptions.ConnectionClosed:
            pass


def make_tab(bc, Connection, cdp):
    """a target Connection whose _owner.connection is the browser connection bc"""
    import types

    owner = types.SimpleNamespace(connection=bc, config=None)
    ti = cdp.target.TargetInfo(
        target_id=cdp.target.TargetID("T1"),
        type_="page",
        title="",
        url="about:blank",
        attached=False,
        can_access_opener=False,
    )
    return Connection("ws://unused/devtools/page/T1", target=ti, _owner=owner)
