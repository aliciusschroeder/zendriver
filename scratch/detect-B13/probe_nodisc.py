import asyncio, time
import zendriver as zd
from zendriver import cdp

async def main():
    config = zd.Config(headless=True)
    config.autodiscover_targets = False
    browser = await zd.Browser.create(config)
    try:
        # Browser.get on existing tab
        t0 = time.monotonic()
        try:
            tab = await asyncio.wait_for(browser.get("data:text/html,<p>hi</p>", timeout=3), 20)
            print(f"Browser.get ok after {time.monotonic()-t0:.1f}s url={tab.url}")
        except asyncio.TimeoutError as e:
            print(f"Browser.get TimeoutError after {time.monotonic()-t0:.1f}s: {e!r}")
            tab = browser.main_tab
            await tab
            print("but tab actually navigated? url:", (await tab.evaluate("location.href")))
        # Browser.get new tab
        t0 = time.monotonic()
        try:
            tab2 = await asyncio.wait_for(browser.get("data:text/html,<p>two</p>", new_tab=True, timeout=3), 20)
            print(f"Browser.get(new_tab) ok after {time.monotonic()-t0:.1f}s")
        except asyncio.TimeoutError as e:
            print(f"Browser.get(new_tab) TimeoutError after {time.monotonic()-t0:.1f}s: {e!r}")
            await browser.update_targets()
            tab2 = browser.tabs[-1]
        # Tab.close
        tid = tab2.target_id
        t0 = time.monotonic()
        try:
            await asyncio.wait_for(tab2.close(), 20)
            print(f"Tab.close ok after {time.monotonic()-t0:.1f}s")
        except asyncio.TimeoutError as e:
            print(f"Tab.close TimeoutError after {time.monotonic()-t0:.1f}s: {e!r}")
        targets = await browser.connection.send(cdp.target.get_targets())
        print("closed target still exists:", any(t.target_id == tid for t in targets))
    finally:
        await asyncio.wait_for(browser.stop(), 15)

asyncio.run(main())
