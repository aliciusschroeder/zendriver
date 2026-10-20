import asyncio, sys
sys.path.insert(0, sys.argv[1]) if len(sys.argv) > 1 else None
import websockets
import zendriver as zd
from zendriver.core.connection import Connection
sys.path.insert(0, "/tmp/claude-0/-home-user-zendriver/b2021b39-94e6-5220-9e66-7f33c0314a80/scratchpad/verify/Q7-fixsafety")
from test_q7_repo_style import FakeWebSocket

async def main():
    ws = FakeWebSocket()
    async def connect(*a, **k): return ws
    websockets.connect = connect
    c = Connection("ws://fake/devtools/page/fake")
    h = lambda e: None
    c.add_handler(zd.cdp.network.RequestWillBeSent, h)
    await asyncio.wait_for(c.send(zd.cdp.page.bring_to_front()), 5)
    c.remove_handlers(zd.cdp.network.RequestWillBeSent, h)
    c.add_handler(zd.cdp.log.EntryAdded, h)
    ws.methods.clear()
    try:
        await asyncio.wait_for(c.send(zd.cdp.page.bring_to_front()), 5)
        print("send OK")
    except ValueError as e:
        print("send raised ValueError:", e)
    print("methods sent on the wire:", ws.methods)
    print("pending tx left in mapper:", [(k, t.method, t.done()) for k, t in c.mapper.items()])
    print("enabled_domains:", [m.__name__ for m in c.enabled_domains])
    await c.aclose()
asyncio.run(main())
