"""like probe_fake_dialog_wedge, but with handlers for two lazily enabled domains"""

import asyncio
import json
import sys

import websockets

import zendriver as zd
from zendriver import cdp
from zendriver.core.connection import Connection


class DialogPage:
    def __init__(self):
        self.frames = asyncio.Queue()
        self.blocked = True
        self.held = []
        self.closed = False
        self.methods = []

    async def send(self, message):
        cmd = json.loads(message)
        self.methods.append(cmd["method"])
        reply = {"id": cmd["id"], "result": {}}
        if cmd["method"] == "Page.handleJavaScriptDialog":
            self.blocked = False
            self.frames.put_nowait(reply)
            for r in self.held:
                self.frames.put_nowait(r)
            self.held.clear()
        elif self.blocked:
            self.held.append(reply)
        else:
            self.frames.put_nowait(reply)

    async def recv(self):
        return json.dumps(await self.frames.get())

    async def close(self):
        self.closed = True


async def main():
    print("python", sys.version.split()[0], zd.__file__)
    page = DialogPage()

    async def connect(*a, **k):
        return page

    websockets.connect = connect
    conn = Connection("ws://fake/devtools/page/X")
    conn.add_handler(cdp.log.EntryAdded, lambda e: None)
    conn.add_handler(cdp.runtime.ConsoleAPICalled, lambda e: None)
    try:
        try:
            await asyncio.wait_for(conn.send(cdp.dom.get_document(-1, True)), 0.5)
        except asyncio.TimeoutError:
            print(
                "bounded call: TimeoutError; enabled_domains =",
                [m.__name__ for m in conn.enabled_domains],
            )
        for attempt in range(3):
            try:
                await asyncio.wait_for(
                    conn.send(cdp.page.handle_java_script_dialog(True)), 2
                )
                print(f"dismiss attempt {attempt}: OK")
                break
            except asyncio.TimeoutError:
                print(
                    f"dismiss attempt {attempt}: HUNG (2s safety net); enabled =",
                    [m.__name__ for m in conn.enabled_domains],
                )
        print("methods sent:", page.methods)
    finally:
        await conn.aclose()


asyncio.run(main())
