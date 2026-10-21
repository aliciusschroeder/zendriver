import asyncio, time, sys
import zendriver as zd
from zendriver import cdp
print("zendriver from", zd.__file__, sys.version.split()[0])

async def timed(label, coro, outer=15):
    t = time.monotonic()
    try:
        r = await asyncio.wait_for(coro, outer)
        print(f"{label}: OK in {time.monotonic()-t:.2f}s")
        return r
    except BaseException as e:
        print(f"{label}: {type(e).__name__} after {time.monotonic()-t:.2f}s {e!r}"[:300])
        return None

async def main():
    cfg = zd.Config(headless=True)
    cfg.autodiscover_targets = False
    b = await zd.Browser.create(cfg)
    try:
        print("tabs at start:", [(t.target_id[:6], t.url) for t in b.tabs])
        await timed("browser.get(data url, timeout=3)", b.get("data:text/html,<title>hi</title>", timeout=3))
        print("tab0 title via evaluate:", await b.tabs[0].evaluate("document.title"))
        await timed("browser.get(new_tab, timeout=3)", b.get("data:text/html,<title>two</title>", new_tab=True, timeout=3))
        await b.update_targets()
        print("tabs after:", [(t.target_id[:6], t.url) for t in b.tabs])
        tab2 = b.tabs[-1]
        await timed("tab.close()", tab2.close())
        live = await b._get_targets()
        print("live page targets:", [(t.target_id[:6], t.url) for t in live if t.type_ == "page"])
        await b.update_targets()
        print("browser.tabs after update_targets:", [(t.target_id[:6], t.url) for t in b.tabs])
        # A4.4: close first tab, then update_targets, then browser.get
        first = b.tabs[0]
        # need another tab to remain
        await b.connection.send(cdp.target.create_target("about:blank"))
        await b.update_targets()
        await b.connection.send(cdp.target.close_target(first.target_id))
        await asyncio.sleep(0.5)
        await b.update_targets()
        live = await b._get_targets()
        print("live page targets:", [t.target_id[:6] for t in live if t.type_ == "page"])
        print("browser.tabs:", [t.target_id[:6] for t in b.tabs])
        print("main_tab is closed first tab:", b.main_tab is first)
        await timed("browser.get after closing first tab", b.get("data:text/html,x", timeout=3))
    finally:
        await b.stop()

asyncio.run(main())
