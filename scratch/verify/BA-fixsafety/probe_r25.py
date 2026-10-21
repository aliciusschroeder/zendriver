"""R25 probe: autodiscover_targets=False."""

import asyncio
import sys
import time

import zendriver as zd
from zendriver import cdp

print("zendriver from", zd.__file__, "python", sys.version.split()[0])


async def timed(label, coro, t_out=30):
    t = time.monotonic()
    try:
        r = await asyncio.wait_for(coro, t_out)
        print(f"{label}: OK in {time.monotonic() - t:.2f}s -> {r!r}"[:200])
        return r
    except BaseException as e:
        print(f"{label}: {type(e).__name__} after {time.monotonic() - t:.2f}s {e}"[:300])
        return None


async def main():
    cfg = zd.Config(headless=True)
    cfg.autodiscover_targets = False
    browser = await zd.Browser.create(cfg)
    try:
        await timed("browser.get(data)", browser.get("data:text/html,<title>one</title>", timeout=3))
        print("  tab0 title:", await browser.tabs[0].evaluate("document.title"))
        await timed(
            "browser.get(new_tab)",
            browser.get("data:text/html,<title>two</title>", new_tab=True, timeout=3),
        )
        await browser.update_targets()
        print("  tabs:", [(t.target_id[:6], t.url) for t in browser.tabs])
        second = browser.tabs[1]
        first = browser.tabs[0]
        await timed("tab.close(first)", first.close(), 20)
        live = [t.target_id for t in await browser._get_targets() if t.type_ == "page"]
        await browser.update_targets()
        print("  live page targets:", [x[:6] for x in live])
        print("  browser.tabs after update_targets:", [t.target_id[:6] for t in browser.tabs])
        print("  main_tab is closed first:", browser.main_tab is first)
        await timed("browser.get after close", browser.get("data:text/html,three", timeout=3))
        _ = second
    finally:
        await browser.stop()


asyncio.run(main())
