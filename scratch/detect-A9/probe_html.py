import asyncio
import zendriver as zd
from zendriver import cdp

async def main():
    browser = await zd.start(headless=True)
    tab = await browser.get("data:text/html,<p>hello</p>")
    await tab.wait_for_ready_state("complete")
    doc = await tab.send(cdp.dom.get_document(-1, True))
    html = await zd.util.html_from_tree(doc, tab)
    print("html_from_tree(document):", repr(html))
    print("'hello' occurs", html.count("hello"), "times; real page:", repr(await tab.get_content()))
    await browser.stop()
asyncio.run(main())
