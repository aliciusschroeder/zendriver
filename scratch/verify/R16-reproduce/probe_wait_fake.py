"""B14.5 (fake peer): Connection.wait() while busy, then the listener stops."""

import asyncio
import sys

sys.path.insert(0, __file__.rsplit("/", 1)[0])

import zendriver
from zendriver.core.connection import Connection

from fake_cdp import FakeCDP

print("zendriver from", zendriver.__file__, "python", sys.version.split()[0])


async def run(variant: str) -> None:
    peer = await FakeCDP(flood_interval=0.03).start()  # event every 30ms -> never idle
    conn = Connection(peer.url)
    await conn.aopen()
    waiter = asyncio.create_task(conn.wait())
    await asyncio.sleep(0.5)
    print(f"[{variant}] waiter done after 0.5s busy: {waiter.done()}")
    old_listener = conn.listener
    if variant == "control":
        peer.flooding = False  # page goes idle
    elif variant == "cancel":
        conn.listener.cancel()  # what _detach_session() does
    elif variant == "peer-close":
        await peer.close_all()  # browser websocket closes
    done, _ = await asyncio.wait({waiter}, timeout=5)
    print(f"[{variant}] waiter done 5s after the change: {bool(done)}; "
          f"old listener running={old_listener.running} idle={old_listener.idle.is_set()}")
    if not done:
        print(f"[{variant}] HANG; stack of stuck waiter:")
        waiter.print_stack(file=sys.stdout)
        waiter.cancel()
        try:
            await waiter
        except asyncio.CancelledError:
            pass
    await conn.aclose()
    await peer.stop()


async def main() -> None:
    for v in ("control", "cancel", "peer-close"):
        await asyncio.wait_for(run(v), 30)


asyncio.run(main())
