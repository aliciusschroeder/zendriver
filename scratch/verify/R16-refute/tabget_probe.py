"""B14.5 via Tab.get(url) (same tab) and `await tab` on a busy page closed from another task."""
import asyncio, sys, time
import zendriver
from zendriver import cdp
print("zendriver from", zendriver.__file__, "python", sys.version.split()[0])
BUSY = "data:text/html,<script>setInterval(()=>console.log('x'),40)</script>"

async def main():
    browser = await zendriver.start(headless=True)
    try:
        tab = await browser.get("data:text/html,<p>start</p>", new_tab=True)
        tab.add_handler(cdp.runtime.ConsoleAPICalled, lambda e: None)
        await tab.send(cdp.runtime.enable())
        g = asyncio.create_task(tab.get(BUSY))
        await asyncio.sleep(0.8)
        print("Tab.get still running before close (busy page, expected):", not g.done())
        await browser.connection.send(cdp.target.close_target(tab.target_id))
        done, _ = await asyncio.wait({g}, timeout=6)
        if g.done():
            print("Tab.get finished:", g.exception())
        else:
            print("Tab.get STILL PENDING 6s after the tab closed -> HANG")
            g.print_stack(limit=2)
            g.cancel()
            try: await g
            except BaseException: pass
    finally:
        await browser.stop()
asyncio.run(main())
