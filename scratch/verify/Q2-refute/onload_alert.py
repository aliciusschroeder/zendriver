"""Realism: plain script, fresh browser, no handlers: get a page that alerts on
load, then select an element that EXISTS with timeout=3."""
import asyncio
import io
import sys
import time

import zendriver

print("zendriver from", zendriver.__file__, "python", sys.version.split()[0])


async def main():
    browser = await zendriver.start(headless=True)
    try:
        t0 = time.monotonic()
        tab = await browser.get("data:text/html,<p id='a'>hi</p><script>alert('welcome')</script>")
        print(f"browser.get returned after {time.monotonic()-t0:.2f}s")
        task = asyncio.ensure_future(tab.select("#a", timeout=3))
        done, _ = await asyncio.wait({task}, timeout=20)
        if task in done:
            print("select finished:", task.exception() or task.result())
        else:
            buf = io.StringIO()
            task.print_stack(file=buf, limit=2)
            print("select(#a, timeout=3) STILL PENDING after 20s; stack:\n" + buf.getvalue())
            task.cancel()
        print("recovery: navigate elsewhere (Page.navigate is browser-side)")
        t0 = time.monotonic()
        await asyncio.wait_for(tab.get("data:text/html,<p id='b'>ok</p>"), 15)
        el = await asyncio.wait_for(tab.select("#b", timeout=3), 10)
        print(f"after navigation select works: {el} ({time.monotonic()-t0:.2f}s)")
    finally:
        await browser.stop()


asyncio.run(main())
