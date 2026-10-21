"""Extras: (a) headless mode concurrent first sends -> setUserAgentOverride sent
twice; (b) the orphan tx left in mapper by the detach race is failed by the
next detach and reported as 'exception was never retrieved'."""
import asyncio
import collections
import gc
import json
import sys

import websockets.asyncio.client as wsc

import zendriver as zd

print("zendriver from", zd.__file__, "python", sys.version.split()[0])
counts: collections.Counter = collections.Counter()
_orig_send = wsc.ClientConnection.send


async def counting_send(self, message, *a, **kw):
    m = json.loads(message)
    counts[(m.get("sessionId"), m.get("method"))] += 1
    return await _orig_send(self, message, *a, **kw)


wsc.ClientConnection.send = counting_send
loop_errors = []


async def main():
    asyncio.get_running_loop().set_exception_handler(
        lambda loop, ctx: loop_errors.append(f"{ctx.get('message')} | {ctx.get('exception')!r}")
    )
    browser = await zd.start(headless=True)
    try:
        # (a)
        tab = await browser.get("about:blank", new_tab=True)
        await asyncio.wait_for(asyncio.gather(tab.evaluate("1"), tab.evaluate("2")), 30)
        print("(a) setUserAgentOverride sent:", counts[(tab.session_id, "Network.setUserAgentOverride")])
        await tab.close()

        # (b)
        tab = await browser.get("about:blank", new_tab=True)

        async def closer():
            while tab.session_id is None:
                await asyncio.sleep(0)
            await tab.aclose()

        await asyncio.wait_for(asyncio.gather(tab.evaluate("1"), closer(), return_exceptions=True), 30)
        orphan = list(tab.mapper.values())
        print("(b) orphans in mapper after race:", orphan and [t.method for t in orphan])
        await asyncio.wait_for(tab.evaluate("2"), 30)  # reattach
        print("(b) orphans still in mapper after reattach:", [t.method for t in tab.mapper.values()])
        await tab.aclose()  # next detach fails the orphan
        del orphan
        gc.collect()
        await asyncio.sleep(0.1)
        gc.collect()
        await tab.close()
    finally:
        await browser.stop()
    gc.collect()
    print("loop errors:")
    for e in loop_errors:
        print("  ", e[:160])


asyncio.run(main())
