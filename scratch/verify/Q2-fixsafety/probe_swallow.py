"""Does Connection._register_handlers' bare `except:` swallow the timeout's cancellation?

alert() open, then a handler for a not-yet-enabled DOM event is added, then a
bounded polling call runs: its first send() goes through _register_handlers,
which sends DOM.enable (unanswered while the dialog is up).
"""

import asyncio
import sys
import time

import zendriver
from zendriver import cdp

print("zendriver from", zendriver.__file__)


async def main():
    browser = await zendriver.start(headless=True)
    try:
        tab = browser.main_tab
        await tab.get("data:text/html,<p id=topp>hi</p>")
        await tab.select("#topp", timeout=5)
        await tab.evaluate("setTimeout(()=>alert('x'),100)", await_promise=False)
        await asyncio.sleep(0.6)
        tab.add_handler(cdp.dom.DocumentUpdated, lambda ev: None)
        for name, factory in [
            ("select('#topp', timeout=1)", lambda: tab.select("#topp", timeout=1)),
            ("wait_for_ready_state(timeout=1)", lambda: tab.wait_for_ready_state("complete", timeout=1)),
        ]:
            t0 = time.monotonic()
            task = asyncio.ensure_future(factory())
            done, _ = await asyncio.wait({task}, timeout=8)
            if done:
                exc = task.exception()
                print(f"{name}: {type(exc).__name__ if exc else 'ok'}({exc}) after {time.monotonic() - t0:.2f}s")
            else:
                print(f"{name}: STILL PENDING after {time.monotonic() - t0:.1f}s")
                task.print_stack(limit=6, file=sys.stdout)
                task.cancel()
                try:
                    await asyncio.wait_for(task, 3)
                except BaseException as e:  # noqa
                    print("   after cancel():", type(e).__name__)
    finally:
        await browser.stop()


asyncio.run(main())
