"""Real-Chromium check: polling methods must return/raise within ~timeout while an alert() is open."""

import asyncio
import sys
import time

import zendriver as zd
from zendriver.core import cloudflare

PAGE = "data:text/html,<p id=topp>hello</p><li aria-label='Apples (42)'>Apples</li>"

CASES = {
    "select_missing": lambda t: t.select("#nope", timeout=2),
    "select_existing": lambda t: t.select("#topp", timeout=2),
    "select_frames": lambda t: t.select("#nope", timeout=2, include_frames=True),
    "find": lambda t: t.find("nope", timeout=2),
    "find_all": lambda t: t.find_all("nope", timeout=2),
    "select_all": lambda t: t.select_all("#nope", timeout=2),
    "xpath": lambda t: t.xpath("//nope", timeout=2),
    "wait_for": lambda t: t.wait_for(selector="#nope", timeout=2),
    "wait_for_text": lambda t: t.wait_for(text="nope", timeout=2),
    "call": lambda t: t(selector="#nope", timeout=2),
    "cf_present": lambda t: cloudflare.cf_is_interactive_challenge_present(t, timeout=2),
    "verify_cf": lambda t: t.verify_cf(timeout=2),
}


async def main() -> None:
    print("zendriver from", zd.__file__, sys.version.split()[0])
    browser = await zd.start(headless=True)
    try:
        # sanity on an unblocked page
        tab = await browser.get(PAGE)
        r = await tab.xpath("//p[@id='topp']", timeout=0)
        print("xpath timeout=0 unblocked ->", len(r), "item(s)")
        t0 = time.monotonic()
        r = await tab.select("#topp", timeout=2)
        print(f"select existing unblocked -> {r.tag} in {time.monotonic() - t0:.3f}s")

        names = sys.argv[1:] or list(CASES)
        for name in names:
            tab = await browser.get(PAGE, new_tab=True)
            await tab.evaluate("setTimeout(() => alert('blocking'), 100)", await_promise=False)
            await asyncio.sleep(0.6)
            t0 = time.monotonic()
            task = asyncio.ensure_future(CASES[name](tab))
            done, _ = await asyncio.wait({task}, timeout=10)
            dt = time.monotonic() - t0
            if not done:
                print(f"[{name}] STILL PENDING after {dt:.2f}s")
                task.print_stack()
                task.cancel()
                continue
            exc = task.exception()
            if exc is not None:
                print(f"[{name}] {dt:.2f}s -> {type(exc).__module__}.{type(exc).__name__}: {exc}")
            else:
                print(f"[{name}] {dt:.2f}s -> {task.result()!r}")
    finally:
        await browser.stop()


asyncio.run(main())
