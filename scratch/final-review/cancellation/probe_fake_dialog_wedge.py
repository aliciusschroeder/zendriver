"""browser-free: a fake page that is 'blocked by a dialog': it answers nothing
that needs the renderer (Log.enable, DOM.getDocument) until it receives
Page.handleJavaScriptDialog, which it answers at once and which unblocks it."""
import asyncio, json, sys
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
    conn.add_handler(cdp.log.EntryAdded, lambda e: None)  # Log not enabled yet
    try:
        try:
            # stands in for the asyncio.wait_for that Q2 puts around tab.select()
            await asyncio.wait_for(conn.send(cdp.dom.get_document(-1, True)), 0.5)
        except asyncio.TimeoutError:
            print("bounded call: TimeoutError; enabled_domains =", conn.enabled_domains)
        try:
            await asyncio.wait_for(conn.send(cdp.page.handle_java_script_dialog(True)), 3)
            print("dismiss: OK")
        except asyncio.TimeoutError:
            print("dismiss: HUNG (3s safety net)")
        print("methods sent:", page.methods)
    finally:
        await conn.aclose()

asyncio.run(main())
