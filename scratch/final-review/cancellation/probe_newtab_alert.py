"""
Real headless chromium: a new tab whose page opens alert() on load, so the
tab's flat session is attached (and _prepare_headless runs) while the dialog
is open. A bounded Q2 call times out; then the user tries to recover.

usage: python probe_newtab_alert.py [headless=1]
"""

import asyncio
import logging
import os
import sys
import time

import zendriver as zd
from zendriver import cdp

logging.basicConfig(level=logging.WARNING, format="%(levelname)s %(name)s: %(message)s")


def dump(tab: zd.Tab, label: str) -> None:
    pending = {k: (v.method, v.done()) for k, v in tab.mapper.items()}
    print(
        f"  [{label}] session={tab.session_id is not None}"
        f" prep_headless_done={tab.__dict__.get('_prep_headless_done')}"
        f" enabled={[m.__name__.split('.')[-1] for m in tab.enabled_domains]}"
        f" mapper={pending}",
        flush=True,
    )


async def timed(label: str, coro, net: float = 8) -> object:
    t0 = time.monotonic()
    try:
        r = await asyncio.wait_for(coro, net)
        print(f"  {label}: OK {r!r:.60} after {time.monotonic()-t0:.2f}s", flush=True)
        return r
    except asyncio.TimeoutError as e:
        print(f"  {label}: TimeoutError {str(e)[:70]!r} after {time.monotonic()-t0:.2f}s", flush=True)
    except Exception as e:
        print(f"  {label}: {type(e).__name__} {str(e)[:70]!r} after {time.monotonic()-t0:.2f}s", flush=True)


async def main() -> None:
    headless = (sys.argv[1] if len(sys.argv) > 1 else "1") == "1"
    print("python", sys.version.split()[0], "zendriver", zd.__file__, "headless", headless, flush=True)
    browser = await zd.start(
        headless=headless,
        sandbox=False,
        browser_executable_path=os.environ["CHROME"],
    )
    try:
        url = "data:text/html,<p id=hello>hello</p><script>alert('on load')</script>"
        tab = await browser.get(url, new_tab=True)
        await asyncio.sleep(0.5)
        dump(tab, "new tab, not used yet")
        await timed("tab.select('#hello', timeout=1)", tab.select("#hello", timeout=1))
        dump(tab, "after first call")
        await timed("tab.send(Page.enable)", tab.send(cdp.page.enable()))
        dump(tab, "after page.enable")
        await timed(
            "tab.send(Page.handleJavaScriptDialog)",
            tab.send(cdp.page.handle_java_script_dialog(accept=True)),
        )
        dump(tab, "after dismiss")
        await timed("tab.select('#hello', timeout=2)", tab.select("#hello", timeout=2))
        dump(tab, "end")
    finally:
        t0 = time.monotonic()
        await asyncio.wait_for(browser.stop(), 60)
        print(f"  stop took {time.monotonic()-t0:.2f}s, process gone: {browser._process is None}", flush=True)


asyncio.run(main())
