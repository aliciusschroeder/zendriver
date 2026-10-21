"""
Deterministic check: the caller's task is cancelled in the same event loop
iteration in which the polling attempt of tab.select() finds the element.

python < 3.12: asyncio.wait_for (wrapped around the poll by Q2) returns the
inner result when the outer is cancelled while the inner is already done, so
the cancellation is lost. on base (no wait_for in select) the CancelledError is
delivered at the `await` in select.
"""

import asyncio
import sys

import zendriver as zd
from zendriver import cdp


async def main() -> None:
    print("python", sys.version.split()[0], zd.__file__)
    tab = zd.Tab(
        "ws://fake/devtools/page/T1",
        target=cdp.target.TargetInfo(
            target_id=cdp.target.TargetID("T1"),
            type_="page",
            title="",
            url="about:blank",
            attached=False,
            can_access_opener=False,
        ),
    )
    found = asyncio.get_running_loop().create_future()

    async def query_selector(selector: str, _node: object = None) -> object:
        return await found

    tab.query_selector = query_selector  # instance patch

    results = []
    for i in range(5):
        found = asyncio.get_running_loop().create_future()

        async def run() -> object:
            el = await tab.select("#x", timeout=5)
            # a correctly cancelled task never gets here
            await asyncio.sleep(0)
            return el

        task = asyncio.create_task(run())
        await asyncio.sleep(0.05)  # task now waits in query_selector
        # the CDP answer arrives and the caller is cancelled in the same iteration
        found.set_result("ELEMENT")
        task.cancel()
        done, _ = await asyncio.wait({task}, timeout=5)
        if task.cancelled():
            results.append("cancelled")
        elif task.done():
            results.append(f"returned {task.result()!r} (cancellation lost)")
        else:
            results.append("still running")
            task.cancel()
    print(results)


asyncio.run(main())
