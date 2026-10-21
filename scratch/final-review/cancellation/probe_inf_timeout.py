import asyncio, sys
import zendriver as zd
from zendriver import cdp

async def main():
    tab = zd.Tab("ws://fake/devtools/page/T1", target=cdp.target.TargetInfo(
        target_id=cdp.target.TargetID("T1"), type_="page", title="", url="about:blank",
        attached=False, can_access_opener=False))
    n = 0
    async def query_selector(selector, _node=None):
        nonlocal n
        n += 1
        await asyncio.sleep(0.05)
        return "EL" if n >= 3 else None
    async def sleep(t=0.25):
        await asyncio.sleep(t)
    tab.query_selector = query_selector
    tab.sleep = sleep
    for t in (float("inf"), 1e18, 10**30):
        n = 0
        try:
            r = await asyncio.wait_for(tab.select("#x", timeout=t), 10)
            print(sys.version.split()[0], "timeout", t, "->", r)
        except BaseException as e:
            print(sys.version.split()[0], "timeout", t, "->", type(e).__name__, e)
asyncio.run(main())
