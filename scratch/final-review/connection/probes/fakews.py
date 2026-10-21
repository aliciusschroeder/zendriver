import asyncio, json, types
from typing import Any, Callable

import websockets
import zendriver as zd
from zendriver.core.connection import Connection, Listener


class FakeWS:
    """script(command) -> list of frames to queue (dict/str/Exception);
    the literal string 'REPLY' marks where the normal reply goes; if the list
    does not contain 'REPLY' the reply is appended at the end. Return None for
    the default (reply only); return [] to never reply."""

    def __init__(self, results=None, script=None):
        self.closed = False
        self.results = results or {}
        self.script = script
        self.frames: asyncio.Queue = asyncio.Queue()
        self.sent: list[dict] = []
        self.concurrent_recv = 0
        self.max_concurrent_recv = 0
        self.recv_errors: list[BaseException] = []

    def reply_for(self, command):
        reply = {"id": command["id"], "result": self.results.get(command["method"], {})}
        if "sessionId" in command:
            reply["sessionId"] = command["sessionId"]
        return reply

    async def send(self, message: str) -> None:
        if self.closed:
            raise websockets.exceptions.ConnectionClosedOK(None, None)
        command = json.loads(message)
        self.sent.append(command)
        frames = self.script(command) if self.script else None
        if frames is None:
            frames = ["REPLY"]
        for f in frames:
            if isinstance(f, str) and f == "REPLY":
                self.frames.put_nowait(self.reply_for(command))
            else:
                self.frames.put_nowait(f)

    async def recv(self) -> str:
        self.concurrent_recv += 1
        self.max_concurrent_recv = max(self.max_concurrent_recv, self.concurrent_recv)
        try:
            if self.concurrent_recv > 1:
                raise RuntimeError("ConcurrencyError: two readers")
            frame = await self.frames.get()
            if isinstance(frame, BaseException):
                raise frame
            return frame if isinstance(frame, str) else json.dumps(frame)
        finally:
            self.concurrent_recv -= 1

    async def close(self) -> None:
        self.closed = True


def use(ws):
    async def connect(*a, **k):
        return ws
    websockets.connect = connect


def tab_for(browser_connection, target_id="T1", config=None):
    browser = types.SimpleNamespace(connection=browser_connection, config=config,
                                    _headless_user_agent=None)
    return Connection(
        f"ws://fake/devtools/page/{target_id}",
        target=zd.cdp.target.TargetInfo(
            target_id=zd.cdp.target.TargetID(target_id), type_="page", title="",
            url="about:blank", attached=False, can_access_opener=False),
        _owner=browser,
    )


def listener_tasks():
    out = []
    for t in asyncio.all_tasks():
        coro = t.get_coro()
        if getattr(coro, "__qualname__", "") == "Listener.listener_loop":
            out.append(t)
    return out


def dump_tasks():
    for t in asyncio.all_tasks():
        if t is asyncio.current_task():
            continue
        print("TASK", t.get_name(), t.get_coro())
        t.print_stack(limit=8)
