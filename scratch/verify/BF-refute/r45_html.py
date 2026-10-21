import asyncio, sys
import zendriver as zd
from zendriver import cdp, util
print("zendriver from", zd.__file__, sys.version.split()[0])
async def main():
    browser = await zd.start(headless=True)
    try:
        tab = await browser.get("data:text/html,<p>hello</p>")
        await asyncio.sleep(0.5)
        doc = await tab.send(cdp.dom.get_document(-1, True))
        html = await util.html_from_tree(doc, tab)
        print("html_from_tree(doc):", repr(html), "| hello count", html.count("hello"))
        print("get_content():", repr(await tab.get_content()))
        el = await tab.select("body")
        h2 = await util.html_from_tree(el, tab)
        print("html_from_tree(body Element):", repr(h2))
        h3 = await util.html_from_tree(el.node, tab)
        print("html_from_tree(body node):", repr(h3))
    finally:
        await browser.stop()
asyncio.run(asyncio.wait_for(main(), 60))
