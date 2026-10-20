import asyncio
import zendriver as zd
from zendriver import cdp

PAGE = "data:text/html,<p id=outer>outside text</p><iframe srcdoc=\"<p id=inner>inside text</p>\"></iframe>"
async def main():
    browser = await zd.start(headless=True)
    tab = await browser.get(PAGE)
    await tab.wait_for_ready_state("complete")
    await asyncio.sleep(0.5)
    inner = await asyncio.wait_for(tab.find("inside text", best_match=False), 10)
    print("found:", inner.tag, inner.attrs)
    await asyncio.wait_for(inner.remove_from_dom(), 10)
    still = await tab.evaluate("document.querySelector('iframe').contentDocument.querySelector('#inner') !== null")
    print("inner <p> still in iframe after remove_from_dom():", still)
    outer = await tab.find("outside text", best_match=False)
    await outer.remove_from_dom()
    print("outer <p> still in page after remove_from_dom():", await tab.evaluate("document.querySelector('#outer') !== null"))
    await browser.stop()
asyncio.run(main())
