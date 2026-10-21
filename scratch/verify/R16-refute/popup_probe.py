"""Natural pattern: click a button whose handler calls window.close(), then `await tab`. No domains enabled."""

import asyncio
import sys
import time

import zendriver

print("zendriver from", zendriver.__file__, "python", sys.version.split()[0])

PAGE = "data:text/html,<title>popup</title><button onclick='window.close()'>Done</button>"


async def main() -> None:
    browser = await zendriver.start(headless=True)
    hangs = 0
    runs = 6
    try:
        for i in range(runs):
            tab = await browser.get(PAGE, new_tab=True)
            btn = await tab.select("button")
            await btn.click()
            t0 = time.monotonic()
            w = asyncio.create_task(tab.wait())  # == `await tab`
            done, _ = await asyncio.wait({w}, timeout=5)
            if w.done():
                print(f"run {i}: returned/raised after {time.monotonic()-t0:.2f}s exc={w.exception()!r}")
            else:
                hangs += 1
                print(f"run {i}: HANG >5s (listener running={tab.listener.running}, session_id={tab.session_id})")
                w.cancel()
                try:
                    await w
                except BaseException:
                    pass
        print(f"hangs: {hangs}/{runs}")
    finally:
        await browser.stop()


asyncio.run(main())
