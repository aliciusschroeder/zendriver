import asyncio

import zendriver as zd

HTML = "data:text/html,<body><p id=p>x</p><br id=b clear=all><div id=d>y</div></body>"


async def main() -> None:
    print("zendriver from", zd.__file__)
    browser = await zd.start(headless=True)
    try:
        tab = await browser.get(HTML)
        for sel in ("#p", "#b"):
            # control: stale node id after another select (DOM.getDocument)
            el = await tab.select(sel)
            await el.update()
            await tab.select("#d")
            try:
                await el.save_to_dom()
                print("stale save_to_dom OK", sel)
            except Exception as e:
                print("stale save_to_dom FAIL", sel, type(e).__name__, str(e)[:60])
            # fresh: update right before save
            el = await tab.select(sel)
            await el.update()
            try:
                await el.save_to_dom()
                print("fresh save_to_dom OK", sel, el)
            except Exception as e:
                print("fresh save_to_dom FAIL", sel, type(e).__name__, str(e)[:60])
    finally:
        await browser.stop()


asyncio.run(main())
