import asyncio
import zendriver as zd

PAGE = "data:text/html,<p id=outer>outside text</p><iframe srcdoc=\"<div id=box><p id=inner>inside text</p></div>\"></iframe>"
JS_INNER = "document.querySelector('iframe').contentDocument.querySelector('#inner') !== null"
async def main():
    browser = await zd.start(headless=True)
    tab = await browser.get(PAGE)
    await tab.wait_for_ready_state("complete")
    await asyncio.sleep(0.5)
    iframe = await tab.select("iframe")
    inner = await asyncio.wait_for(iframe.query_selector("#inner"), 10)
    print("found via iframe.query_selector:", inner.tag, inner.attrs.get("id"), "parent:", inner.parent and inner.parent.attrs.get("id"))
    await asyncio.wait_for(inner.remove_from_dom(), 10)
    print("parent after remove_from_dom (which calls update):", inner.parent)
    print("inner <p> still in iframe after remove_from_dom():", await tab.evaluate(JS_INNER))
    await browser.stop()
asyncio.run(main())
