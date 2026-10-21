"""Real Chromium: methods on a tab blocked by alert(), then recovery."""

import asyncio
import sys
import time
from typing import Any, Awaitable, Callable

import zendriver as zd
from zendriver.core import cloudflare


async def timed(name: str, make: Callable[[], Awaitable[Any]], net: float = 6) -> None:
    t0 = time.monotonic()
    task = asyncio.ensure_future(make())
    done, _ = await asyncio.wait({task}, timeout=net)
    dt = time.monotonic() - t0
    if not done:
        task.cancel()
        try:
            await asyncio.wait_for(task, 2)
        except BaseException:  # noqa
            pass
        print(f"[{name}] STILL PENDING after {dt:.2f}s")
        return
    exc = task.exception()
    if exc is not None:
        print(f"[{name}] {type(exc).__name__}({exc}) in {dt:.2f}s")
    else:
        r = task.result()
        print(f"[{name}] -> {'element' if r and not isinstance(r, list) else r!r} in {dt:.2f}s")


async def main() -> None:
    print(sys.version.split()[0], zd.__file__)
    browser = await zd.start(headless=True)
    try:
        tab = browser.main_tab
        assert tab is not None
        await tab.get("data:text/html,<p id=topp>hello</p>")
        await tab.evaluate("setTimeout(() => alert('blocking'), 200)", await_promise=False)
        await asyncio.sleep(1)

        await timed("select missing t=2", lambda: tab.select("#nope", timeout=2))
        await timed("select existing t=2", lambda: tab.select("#topp", timeout=2))
        await timed("find t=2", lambda: tab.find("hello", timeout=2))
        await timed("xpath t=2", lambda: tab.xpath("//p", timeout=2))
        await timed("xpath t=0", lambda: tab.xpath("//p", timeout=0))
        await timed("wait_for t=2", lambda: tab.wait_for(selector="#nope", timeout=2))
        await timed("tab() t=2", lambda: tab(selector="#nope", timeout=2))
        await timed(
            "cf_present t=2",
            lambda: cloudflare.cf_is_interactive_challenge_present(tab, timeout=2),
        )
        await timed("verify_cf t=2", lambda: tab.verify_cf(timeout=2, click_delay=1))
        print("pending transactions in mapper:", len(tab.mapper))

        # recovery: navigate away closes the dialog
        await timed("tab.get recovery", lambda: tab.get("data:text/html,<p id=ok>ok</p>"), net=15)
        await asyncio.sleep(0.5)
        await timed("select after recovery", lambda: tab.select("#ok", timeout=2))
        await timed("xpath after recovery", lambda: tab.xpath("//p[@id='ok']", timeout=2))
        await timed("find after recovery", lambda: tab.find("ok", timeout=2))
        await asyncio.sleep(0.5)
        print("pending transactions in mapper after recovery:", len(tab.mapper))
    finally:
        await browser.stop()


asyncio.run(main())
