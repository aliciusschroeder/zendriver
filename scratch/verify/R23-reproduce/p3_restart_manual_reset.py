"""R23 / A3.2 extra: even with host/port reset by hand, stop() keeps stale targets."""
import asyncio

import asyncio_atexit
import zendriver as zd

print("zendriver from", zd.__file__)


async def main():
    b = await zd.start(headless=True)
    old_tab_ids = [t.target_id for t in b.tabs]
    print("first run tabs", old_tab_ids)
    await b.stop()
    b.config.host = None
    b.config.port = None
    await asyncio.wait_for(b.start(), 60)
    print("restart ok, new pid", b._process_pid, "port", b.config.port)
    print("targets after restart:", [(t.target_id, t.closed if hasattr(t, 'closed') else None) for t in b.targets])
    print("first tab is stale (old id):", b.tabs[0].target_id in old_tab_ids)
    loop = asyncio.get_running_loop()
    # is the restarted instance registered with asyncio_atexit again?
    cbs = getattr(asyncio_atexit, "_get_entry", None)
    try:
        entry = asyncio_atexit._get_entry(loop)
        print("atexit callbacks registered:", [getattr(c, "__self__", c) is b for c in entry.callbacks])
    except Exception as e:
        print("could not inspect asyncio_atexit:", repr(e))
    try:
        t = await asyncio.wait_for(b.get("about:blank"), 30)
        print("get after restart ok", t)
    except Exception as e:
        print("get after restart raised", type(e).__name__, " ".join(str(e).split())[:200])
    await b.stop()


asyncio.run(main())
