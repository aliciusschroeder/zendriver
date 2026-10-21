"""real headless Chromium: timeouts during a pending Log.enable on an alert()-blocked page"""

import asyncio
import sys
import time

import zendriver as zd

print(sys.version.split()[0], zd.__file__)


async def timed(label: str, coro: object, limit: float) -> None:
    start = time.monotonic()
    task = asyncio.ensure_future(coro)  # type: ignore[arg-type]
    done, _ = await asyncio.wait({task}, timeout=limit)
    elapsed = time.monotonic() - start
    if not done:
        print(f"[{label}] STILL RUNNING after {elapsed:.2f}s (HANG)")
        task.cancel()
        await asyncio.wait({task}, timeout=2)
        return
    exc = task.exception() if not task.cancelled() else "cancelled"
    print(f"[{label}] finished after {elapsed:.2f}s: {exc!r}")


async def main() -> None:
    browser = await zd.start(headless=True)
    try:
        tab = await browser.get("about:blank")
        await tab.evaluate("setTimeout(() => alert('blocked'), 50)")
        await asyncio.sleep(0.5)
        tab.add_handler(zd.cdp.log.EntryAdded, lambda e: None)
        await timed(
            "wait_for(evaluate, 2)",
            asyncio.wait_for(tab.evaluate("1"), 2),
            8,
        )
        await timed(
            "wait_for_ready_state(timeout=2)",
            tab.wait_for_ready_state("complete", timeout=2),
            8,
        )
        print("Log in enabled_domains:", zd.cdp.log in tab.enabled_domains)
        # close the dialog; the next send must enable Log again
        await tab.send(zd.cdp.page.handle_java_script_dialog(accept=True))
        await asyncio.wait_for(tab.evaluate("1"), 5)
        print("after dismiss, Log in enabled_domains:", zd.cdp.log in tab.enabled_domains)
    finally:
        await browser.stop()


asyncio.run(main())
