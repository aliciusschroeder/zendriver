"""B14.5 (real headless Chromium): Tab.get(url) to a busy page, tab closed while get() waits for idle."""
import asyncio, sys
import zendriver
from zendriver import cdp
print("zendriver from", zendriver.__file__, "python", sys.version.split()[0])
URL = "data:text/html,<script>setInterval(()=>console.log('t'),30)</script>busy"

async def main():
    browser = await zendriver.start(headless=True)
    try:
        tab = await browser.get("about:blank", new_tab=True)
        tab.add_handler(cdp.runtime.ConsoleAPICalled, lambda ev: None)
        await tab.send(cdp.runtime.enable())
        getter = asyncio.create_task(tab.get(URL))
        await asyncio.sleep(1.0)
        print("Tab.get done while page busy:", getter.done())
        await browser.connection.send(cdp.target.close_target(tab.target_id))
        done, _ = await asyncio.wait({getter}, timeout=8)
        print("Tab.get done 8s after closeTarget:", bool(done))
        if not done:
            getter.print_stack(file=sys.stdout)
            getter.cancel()
            try:
                await getter
            except BaseException as e:
                print("after cancel:", type(e).__name__)
        else:
            print("result/exc:", getter.exception())
    finally:
        await browser.stop()

asyncio.run(main())
