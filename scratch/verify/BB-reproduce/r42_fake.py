import asyncio, sys, os
sys.path.insert(0, os.path.dirname(__file__))
import zendriver as zd
from zendriver import cdp
from zendriver.core.connection import Connection, ProtocolException
from fakepeer import FakePeer
print("zendriver from", zd.__file__, "python", sys.version.split()[0])

async def shared_exc():
    print("=== A1.4/A2.9/B15.10 shared ProtocolException on aclose")
    async with FakePeer() as peer:
        peer.drop = {"Target.getTargets", "Target.createTarget", "Browser.getVersion"}
        conn = Connection(peer.url)
        await conn.aopen()
        tasks = [
            asyncio.ensure_future(conn.send(cdp.target.get_targets())),
            asyncio.ensure_future(conn.send(cdp.target.create_target(url="https://secret.example/?token=abc"))),
            asyncio.ensure_future(conn.send(cdp.browser.get_version())),
        ]
        await asyncio.sleep(0.3)
        print("pending mapper ids:", list(conn.mapper))
        await conn.aclose()
        res = await asyncio.wait_for(asyncio.gather(*tasks, return_exceptions=True), 10)
        for i, r in enumerate(res):
            print(f"task {i}: type={type(r).__name__} id={id(r)} str={str(r)!r}")
        print("res[0] is res[1] is res[2]:", res[0] is res[1] is res[2])

async def remove_module():
    print("\n=== A1.7 remove_handlers(module, handler)")
    conn = Connection("ws://127.0.0.1:9/unused")
    h = lambda ev: None
    conn.add_handler(cdp.network, h)
    count = lambda: sum(1 for k, v in conn.handlers.items() if h in v)
    print("event types with h after add_handler(cdp.network, h):", count())
    conn.remove_handlers(cdp.network, h)
    print("after remove_handlers(cdp.network, h):", count())
    conn.remove_handlers(cdp.network)
    print("after remove_handlers(cdp.network):", count())
    print("contains RequestWillBeSent handler:", h in conn.handlers[cdp.network.RequestWillBeSent])

async def main():
    await shared_exc()
    await remove_module()
asyncio.run(asyncio.wait_for(main(), 30))
