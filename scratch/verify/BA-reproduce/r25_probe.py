import asyncio, time, sys
import zendriver as zd
from zendriver import cdp
print("zendriver from", zd.__file__, "python", sys.version.split()[0])

async def main():
    cfg = zd.Config(headless=True)
    cfg.autodiscover_targets = False
    b = await zd.Browser.create(cfg)
    try:
        print("initial tabs", [t.target_id for t in b.tabs])
        # B13.6 / A4.3 / A12.5: Browser.get
        t0 = time.monotonic()
        try:
            r = await asyncio.wait_for(b.get("data:text/html,<title>hi</title><p>hi</p>", timeout=3), 20)
            print(f"Browser.get OK after {time.monotonic()-t0:.2f}s -> {r}")
        except asyncio.TimeoutError as e:
            print(f"Browser.get TimeoutError after {time.monotonic()-t0:.2f}s: {e!r}")
        tab0 = b.tabs[0]
        print("tab0 title after get:", await tab0.evaluate("document.title"), "url:", await tab0.evaluate("location.href"))
        # new tab
        t0 = time.monotonic()
        try:
            r = await asyncio.wait_for(b.get("data:text/html,<title>two</title>", new_tab=True, timeout=3), 20)
            print(f"Browser.get(new_tab) OK after {time.monotonic()-t0:.2f}s")
        except asyncio.TimeoutError as e:
            print(f"Browser.get(new_tab) TimeoutError after {time.monotonic()-t0:.2f}s: {e!r}")
        targets = await b.connection.send(cdp.target.get_targets())
        live = [(t.target_id, t.url) for t in targets if t.type_ == "page"]
        print("live page targets:", live)
        # Tab.get(new_tab=True) delegates
        t0 = time.monotonic()
        try:
            await asyncio.wait_for(tab0.get("data:text/html,<title>three</title>", new_tab=True, timeout=3), 20)
            print(f"Tab.get(new_tab) OK after {time.monotonic()-t0:.2f}s")
        except asyncio.TimeoutError as e:
            print(f"Tab.get(new_tab) TimeoutError after {time.monotonic()-t0:.2f}s: {e!r}")
        # Tab.close
        await b.update_targets()
        print("browser.tabs after update:", [(t.target_id[:8], t.url) for t in b.tabs])
        victim = b.tabs[-1]
        vid = victim.target_id
        t0 = time.monotonic()
        try:
            await asyncio.wait_for(victim.close(), 20)
            print(f"Tab.close OK after {time.monotonic()-t0:.2f}s")
        except asyncio.TimeoutError as e:
            print(f"Tab.close TimeoutError after {time.monotonic()-t0:.2f}s: {e!r}")
        targets = await b.connection.send(cdp.target.get_targets())
        print("closed target still exists in chrome:", any(t.target_id == vid for t in targets))

        # A4.4: update_targets never prunes
        await b.update_targets()
        live_ids = [t.target_id for t in await b.connection.send(cdp.target.get_targets()) if t.type_ == "page"]
        print("chrome live page ids:", [i[:8] for i in live_ids])
        print("browser.tabs ids:     ", [t.target_id[:8] for t in b.tabs])
        print("dead victim still in browser.targets:", any(t.target_id == vid for t in b.targets))
        # close first tab via raw closeTarget, then update_targets
        first = b.tabs[0]
        fid = first.target_id
        await b.connection.send(cdp.target.close_target(fid))
        await asyncio.sleep(0.5)
        await b.update_targets()
        live_ids = [t.target_id for t in await b.connection.send(cdp.target.get_targets()) if t.type_ == "page"]
        print("after closing first: chrome live:", [i[:8] for i in live_ids], "browser.tabs:", [t.target_id[:8] for t in b.tabs])
        print("main_tab is closed first tab:", b.main_tab is first)
        t0 = time.monotonic()
        try:
            await asyncio.wait_for(b.get("data:text/html,x", timeout=3), 20)
            print("browser.get after close-first OK")
        except Exception as e:
            print(f"browser.get after close-first -> {type(e).__name__} after {time.monotonic()-t0:.2f}s: {str(e).splitlines()[0]}")
    finally:
        await b.stop()

asyncio.run(main())
