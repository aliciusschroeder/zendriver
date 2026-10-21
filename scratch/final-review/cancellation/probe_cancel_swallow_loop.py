"""a polling loop over tab.select() is cancelled by a watchdog in the same
event loop iteration in which an attempt finds the element (python < 3.12)."""
import asyncio
import sys

import zendriver as zd
from zendriver import cdp


async def main() -> None:
    print("python", sys.version.split()[0], zd.__file__)
    tab = zd.Tab(
        "ws://fake/devtools/page/T1",
        target=cdp.target.TargetInfo(
            target_id=cdp.target.TargetID("T1"), type_="page", title="",
            url="about:blank", attached=False, can_access_opener=False,
        ),
    )
    loop = asyncio.get_running_loop()
    pending: list[asyncio.Future] = []
    calls = 0

    async def query_selector(selector: str, _node: object = None) -> object:
        nonlocal calls
        calls += 1
        f = loop.create_future()
        pending.append(f)
        return await f

    tab.query_selector = query_selector

    async def scrape_forever() -> None:
        while True:
            await tab.select("#x", timeout=5)

    task = asyncio.create_task(scrape_forever())
    await asyncio.sleep(0.05)
    # watchdog: the answer to the current attempt arrives, and the scraper is
    # cancelled, in the same iteration
    pending[-1].set_result("ELEMENT")
    task.cancel()
    # keep answering later attempts, as a live page would
    for _ in range(20):
        await asyncio.sleep(0.05)
        if pending and not pending[-1].done():
            pending[-1].set_result("ELEMENT")
    done, _ = await asyncio.wait({task}, timeout=1)
    print("task done:", task.done(), "cancelled:", task.cancelled(), "select attempts after cancel():", calls - 1)
    task.cancel()
    await asyncio.wait({task}, timeout=1)


asyncio.run(main())
