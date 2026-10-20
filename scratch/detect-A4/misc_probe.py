import asyncio, sys, types
import zendriver as zd
from zendriver import cdp

async def main():
    b = await zd.start(headless=True)
    try:
        try:
            await b.grant_all_permissions()
            print("grant_all_permissions OK")
        except Exception as e:
            print("grant_all_permissions:", type(e).__name__, str(e)[:300])
        # close every page, then iterate the browser
        for t in list(b.tabs):
            await t.close()
        await asyncio.sleep(0.5)
        print("targets after closing all tabs:", b.targets)
        try:
            print("list(browser):", list(b))
        except Exception as e:
            print("list(browser) after closing all tabs:", type(e).__name__, e)
        try:
            print("main_tab:", b.main_tab)
        except Exception as e:
            print("main_tab:", type(e).__name__, e)
    finally:
        await b.stop()
asyncio.run(main())
