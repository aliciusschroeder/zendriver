"""SEED-C3: does a send() cancelled by wait_for leave its Transaction in mapper?"""

import asyncio
import gc
import sys

sys.path.insert(0, __file__.rsplit("/", 1)[0])

import zendriver
from zendriver import cdp
from zendriver.core.connection import Connection

from fake_cdp import FakeCDP

print("zendriver from", zendriver.__file__, "python", sys.version.split()[0])


async def main() -> None:
    peer = await FakeCDP(drop={"Runtime.evaluate"}).start()
    conn = Connection(peer.url)
    await conn.send(cdp.runtime.run_if_waiting_for_debugger())
    print("mapper after normal send:", len(conn.mapper))

    n = 200
    timeouts = 0
    for i in range(n):
        try:
            await asyncio.wait_for(
                conn.send(cdp.runtime.evaluate("new Promise(()=>{})", await_promise=True)),
                timeout=0.01,
            )
        except asyncio.TimeoutError:
            timeouts += 1
    await asyncio.sleep(1.0)
    gc.collect()
    states = {}
    for tx in conn.mapper.values():
        key = "cancelled" if tx.cancelled() else ("done" if tx.done() else "pending")
        states[key] = states.get(key, 0) + 1
    print(f"timeouts: {timeouts}/{n}; mapper size 1s later: {len(conn.mapper)}; states: {states}")
    print("sample entry:", next(iter(conn.mapper.values())).method if conn.mapper else None)
    # a further normal command does not clean them up
    await conn.send(cdp.runtime.run_if_waiting_for_debugger())
    print("mapper after another normal send:", len(conn.mapper))
    await conn.aclose()
    print("mapper after aclose:", len(conn.mapper))
    await peer.stop()


asyncio.run(main())
