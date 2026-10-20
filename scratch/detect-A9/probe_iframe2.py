import asyncio
import zendriver as zd

PAGE = "data:text/html,<p id=outer>outside text</p><iframe srcdoc=\"<div id=box><p id=inner>inside text</p></div>\"></iframe>"
JS_INNER = "document.querySelector('iframe').contentDocument.querySelector('#inner') !== null"
async def main():
    browser = await zd.start(headless=True)
    tab = await browser.get(PAGE)
    await tab.wait_for_ready_state("complete")
    await asyncio.sleep(0.5)
    ps = await asyncio.wait_for(tab.query_selector_all("p", _include_frames=True), 10)
    print("found:", [(p.tag, p.attrs.get("id")) for p in ps])
    inner = [p for p in ps if p.attrs.get("id") == "inner"][0]
    print("inner.parent before update:", inner.parent and inner.parent.attrs.get("id"))
    await asyncio.wait_for(inner.remove_from_dom(), 10)
    print("inner.parent after update:", inner.parent)
    print("inner <p> still in iframe after remove_from_dom():", await tab.evaluate(JS_INNER))
    outer = [p for p in ps if p.attrs.get("id") == "outer"][0]
    await outer.remove_from_dom()
    print("outer <p> still in page after remove_from_dom():", await tab.evaluate("document.querySelector('#outer') !== null"))
    await browser.stop()
asyncio.run(main())
