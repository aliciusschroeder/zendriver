import asyncio
import sys

sys.path.insert(0, "/tmp/claude-0/-home-user-zendriver/b2021b39-94e6-5220-9e66-7f33c0314a80/scratchpad/detect-A5")
from server import start_server  # noqa

import zendriver as zd
from zendriver import cdp


async def step(name, coro, t=30):
    try:
        r = await asyncio.wait_for(coro, t)
        print(f"[{name}] ->", r)
        return r
    except BaseException as e:
        print(f"[{name}] EXC {type(e).__name__}: {e!s:.300}")
        return None


async def main():
    server, base = start_server()
    browser = await zd.start(headless=True)
    try:
        tab = await browser.get(base + "/table")
        rows = await tab.select_all("tr")
        print("rows", len(rows))

        # does getDocument invalidate node ids?
        r0 = rows[0]
        old_id = r0.node_id
        await tab.send(cdp.dom.get_document(-1, True))
        try:
            res = await tab.send(cdp.dom.query_selector_all(old_id, "td"))
            print("old id still valid ->", res)
        except Exception as e:
            print("old id after getDocument:", type(e).__name__, str(e)[:120])

        # H4: concurrent element queries
        for attempt in range(3):
            rows = await tab.select_all("tr")
            res = await step(
                f"gather qs attempt {attempt}",
                asyncio.gather(*(r.query_selector("td") for r in rows)),
            )
            if res is not None:
                print("  None count:", sum(1 for x in res if x is None), "of", len(res))
            res = await step(
                f"gather qsa attempt {attempt}",
                asyncio.gather(*(r.query_selector_all("td") for r in rows)),
            )
            if res is not None:
                print("  empty count:", sum(1 for x in res if not x), "of", len(res))
            print("  __last leftovers:", sum(1 for r in rows if "__last" in vars(r)))

        # H4b: sequential, after a concurrent stale retry leaves __last set
        rows = await tab.select_all("tr")
        await asyncio.gather(*(r.query_selector("td") for r in rows))
        flagged = [r for r in rows if "__last" in vars(r)]
        print("flagged rows:", len(flagged))
    finally:
        await browser.stop()
        server.shutdown()


asyncio.run(main())
