"""Residual window in fix (4): the parent browser listener stops (receive error)
right after it delivered the reply to a tab's first _prepare_expert oneshot.
The second oneshot is registered after the parent died and after aopen()'s
revival check, so nobody reads its reply."""

import asyncio
import json
import sys
import types
from typing import Any

import websockets

import zendriver as zd
from zendriver.core.connection import Connection

print("python", sys.version.split()[0], "zendriver", zd.__file__)


class Fake:
    def __init__(self) -> None:
        self.closed = False
        self.frames: asyncio.Queue[Any] = asyncio.Queue()
        self.sent: list[dict[str, Any]] = []

    async def send(self, message: str) -> None:
        cmd = json.loads(message)
        self.sent.append(cmd)
        result: dict[str, Any] = {}
        if cmd["method"] == "Target.attachToTarget":
            result = {"sessionId": "S1"}
        if cmd["method"] == "Page.addScriptToEvaluateOnNewDocument":
            result = {"identifier": "1"}
        reply: dict[str, Any] = {"id": cmd["id"], "result": result}
        if "sessionId" in cmd:
            reply["sessionId"] = cmd["sessionId"]
        self.frames.put_nowait(reply)
        if cmd["method"] == "Page.addScriptToEvaluateOnNewDocument":
            # a bad frame right after that reply
            self.frames.put_nowait(RuntimeError("cannot receive"))

    async def recv(self) -> str:
        f = await self.frames.get()
        if isinstance(f, BaseException):
            raise f
        return json.dumps(f)

    async def close(self) -> None:
        self.closed = True


async def main() -> None:
    fake = Fake()

    async def connect(*a: Any, **k: Any) -> Fake:
        return fake

    websockets.connect = connect  # type: ignore[assignment]
    browser_connection = Connection("ws://fake/devtools/browser/fake")
    owner = types.SimpleNamespace(
        connection=browser_connection,
        config=types.SimpleNamespace(expert=True, headless=False),
    )
    tab = Connection(
        "ws://fake/devtools/page/T1",
        target=zd.cdp.target.TargetInfo(
            target_id=zd.cdp.target.TargetID("T1"),
            type_="page",
            title="",
            url="about:blank",
            attached=False,
            can_access_opener=False,
        ),
        _owner=owner,  # type: ignore[arg-type]
    )
    task = asyncio.ensure_future(tab.send(zd.cdp.page.bring_to_front()))
    done, _ = await asyncio.wait({task}, timeout=3)
    if done:
        try:
            print("tab.send finished:", task.result())
        except BaseException as e:
            print("tab.send raised:", repr(e))
    else:
        print("tab.send HUNG for 3s")
        print("  methods sent:", [c["method"] for c in fake.sent])
        print("  tab mapper:", {k: v.method for k, v in tab.mapper.items()})
        bl = browser_connection.listener
        print("  browser listener running:", bl.running if bl else None)
        task.print_stack(limit=3)
        task.cancel()
    await tab.aclose()
    await browser_connection.aclose()


asyncio.run(main())
