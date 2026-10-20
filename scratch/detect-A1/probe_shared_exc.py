"""Probe B: one ProtocolException instance is shared by every pending send and
each send() appends its own command to it."""
import asyncio

from fakecdp import FakeCDP

import zendriver as zd
from zendriver.core.connection import Connection


def behaviour(msg):
    if msg["method"] in ("Target.setDiscoverTargets",):
        return {}
    return "noreply"


async def main() -> None:
    fake = FakeCDP(behaviour)
    url = await fake.start()
    conn = Connection(url)
    await conn.send(zd.cdp.target.set_discover_targets(discover=True))
    tasks = [
        asyncio.create_task(conn.send(zd.cdp.target.get_targets())),
        asyncio.create_task(conn.send(zd.cdp.target.create_target(url="https://secret.example/?token=abc"))),
        asyncio.create_task(conn.send(zd.cdp.browser.get_version())),
    ]
    await asyncio.sleep(0.3)
    await conn.aclose()
    res = await asyncio.wait_for(asyncio.gather(*tasks, return_exceptions=True), 5)
    print("same object:", res[0] is res[1] is res[2])
    for i, e in enumerate(res):
        print(f"--- task {i} str(exc):\n{e}")
    import traceback
    print("--- traceback of task 0 exception (frames):")
    for fs in traceback.extract_tb(res[0].__traceback__):
        print("   ", fs.name, fs.lineno)
    await fake.stop()


asyncio.run(main())
