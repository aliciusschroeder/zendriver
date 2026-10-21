import asyncio, time, sys
import zendriver as zd
from zendriver import cdp
import srv
print("zendriver from", zd.__file__, "python", sys.version.split()[0])

async def pages(b):
    return [(t.target_id[:8], t.url) for t in await b.connection.send(cdp.target.get_targets()) if t.type_ == "page"]

async def timed(label, coro):
    t0 = time.monotonic()
    try:
        r = await asyncio.wait_for(coro, 30)
        print(f"{label}: OK in {time.monotonic()-t0:.2f}s -> {r!r}"[:200])
        return r
    except BaseException as e:
        print(f"{label}: {type(e).__name__} after {time.monotonic()-t0:.2f}s {str(e).splitlines()[0] if str(e) else ''}")

async def main():
    s, B = srv.start()
    b = await zd.start(headless=True)
    try:
        await timed("browser.get(page)", b.get(B + "/page", timeout=3))
        await timed("browser.get(204)", b.get(B + "/204", timeout=3))
        print("  tab0 location after 204:", await b.tabs[0].evaluate("location.href"))
        await timed("browser.get(dl)", b.get(B + "/dl", timeout=3))
        await timed("tab.get(204)", b.tabs[0].get(B + "/204"))
        await timed("tab.get(dl)", b.tabs[0].get(B + "/dl"))
        # raw Page.navigate result for 204
        r = await b.tabs[0].send(cdp.page.navigate(B + "/204?raw"))
        print("  raw Page.navigate(204) ->", r)
        r = await b.tabs[0].send(cdp.page.navigate(B + "/dl?raw"))
        print("  raw Page.navigate(dl) ->", r)

        # SEED-G1: new_tab timing out leaves an orphan tab
        print("pages before new_tab:", await pages(b))
        await timed("browser.get(hang, new_tab, timeout=2)", b.get(B + "/hang", new_tab=True, timeout=2))
        print("pages after hang new_tab:", await pages(b))
        await timed("browser.get(204, new_tab, timeout=2)", b.get(B + "/204?nt", new_tab=True, timeout=2))
        print("pages after 204 new_tab:", await pages(b))
        print("browser.tabs:", [(t.target_id[:8], t.url) for t in b.tabs])
    finally:
        await b.stop()
        s.shutdown()

asyncio.run(main())
