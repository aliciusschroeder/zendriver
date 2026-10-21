import asyncio, sys, logging, os
import zendriver as zd
from zendriver import cdp
print(sys.version.split()[0], zd.__file__)
logging.basicConfig(level=logging.WARNING, format="%(levelname)s %(name)s: %(message)s")

async def main():
    browser = await zd.start(headless=True, sandbox=False, browser_executable_path=os.path.join(os.environ["ZBIN"], "chromium"))
    try:
        tab = await browser.get("about:blank")
        for dom in (cdp.css, cdp.page, cdp.network, cdp.animation, cdp.layer_tree, cdp.service_worker, cdp.web_authn):
            try:
                await browser.connection.send(dom.enable(), _is_update=True)
                print("browser.connection", dom.__name__, "enable ok")
            except Exception as e:
                print("browser.connection", dom.__name__, "enable FAILED:", str(e).splitlines()[0])
        try:
            await tab.send(cdp.css.enable(), _is_update=True); print("tab css enable ok (fresh)")
        except Exception as e:
            print("tab css enable FAILED (fresh):", str(e).splitlines()[0])
        await tab.select("body")
        try:
            await tab.send(cdp.css.enable(), _is_update=True); print("tab css enable ok (after select)")
        except Exception as e:
            print("tab css enable FAILED (after select):", str(e).splitlines()[0])
    finally:
        await asyncio.wait_for(browser.stop(), 60)
asyncio.run(main())
