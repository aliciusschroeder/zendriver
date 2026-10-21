import asyncio, sys, tempfile, pathlib, shutil
import zendriver
from zendriver import cdp
print("zendriver from", zendriver.__file__)
async def state(tab):
    return await tab.evaluate("JSON.stringify([navigator.userAgent.slice(-40), navigator.language, navigator.userAgentData && navigator.userAgentData.brands.length, navigator.userAgentData && navigator.userAgentData.platform])")
async def main(headless):
    d = tempfile.mkdtemp(); p = pathlib.Path(d)/"a.html"; p.write_text("<html><body>x</body></html>")
    browser = await zendriver.start(headless=headless)
    try:
        tab = await browser.get(p.as_uri())
        print("headless", headless, "before:", await state(tab))
        await tab.set_user_agent(accept_language="de-DE"); await tab.reload()
        print("  after set_user_agent(accept_language):", await state(tab))
        await tab.send(cdp.network.set_user_agent_override(user_agent="", accept_language="fr-FR")); await tab.reload()
        print("  after raw override user_agent='' :", await state(tab))
    finally:
        await browser.stop(); shutil.rmtree(d, ignore_errors=True)
asyncio.run(asyncio.wait_for(main(sys.argv[1] == "1"), 60))
