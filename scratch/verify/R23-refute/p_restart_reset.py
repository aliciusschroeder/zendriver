"""Probe: restart after stop with host/port reset by hand -- do stale targets break it?"""
import asyncio
import sys

import zendriver as zd

print("zendriver from", zd.__file__, "python", sys.version.split()[0])


async def main():
    b = await zd.start(headless=True)
    old_ids = [t.target_id for t in b.targets]
    await b.get("data:text/html,<p>hi</p>")
    await b.stop()
    b.config.host = None
    b.config.port = None
    try:
        await asyncio.wait_for(b.start(), 60)
        print("restart OK pid", b._process_pid, "port", b.config.port)
        print("targets:", [(t.target_id[:8], t.target_id in old_ids, t.type_) for t in b.targets])
        print("tabs[0] stale:", b.tabs[0].target_id in old_ids if b.tabs else None)
        try:
            tab = await asyncio.wait_for(b.get("data:text/html,<p>again</p>"), 30)
            print("get OK", await tab.evaluate("1+1"))
        except Exception as e:
            print("get raised", type(e).__name__, str(e)[:200])
        try:
            tab = await asyncio.wait_for(b.get("data:text/html,<p>new</p>", new_tab=True), 30)
            print("get new_tab OK", await tab.evaluate("2+2"))
        except Exception as e:
            print("get new_tab raised", type(e).__name__, str(e)[:200])
    except Exception as e:
        print("restart raised", type(e).__name__, str(e)[:200])
    finally:
        await b.stop()


asyncio.run(main())
