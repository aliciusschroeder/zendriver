import asyncio, sys
sys.path.insert(0, sys.argv[1]) if len(sys.argv) > 1 else None
import zendriver
from zendriver import cdp
from zendriver.core.connection import Connection
sys.path.insert(0, "/tmp/claude-0/-home-user-zendriver/b2021b39-94e6-5220-9e66-7f33c0314a80/scratchpad/verify/R19-fixsafety/tests")
from test_r19_sync_handlers import FakePeer
print("zendriver:", zendriver.__file__)
async def main():
    ran = asyncio.Event()
    async def process(e): ran.set()
    peer = FakePeer()
    async with peer as url:
        conn = Connection(url)
        conn.add_handler(cdp.fetch.RequestPaused, lambda e: asyncio.create_task(process(e)))
        await asyncio.wait_for(conn.send(cdp.fetch.enable()), 5)
        try:
            await asyncio.wait_for(ran.wait(), 2); print("create_task lambda: ran")
        except asyncio.TimeoutError:
            print("create_task lambda: NEVER RAN")
        await conn.aclose()
asyncio.run(main())
