import asyncio, zendriver as zd
from zendriver import cdp
from zendriver.core import util
async def main():
    print("zendriver from", zd.__file__)
    b = await zd.start(headless=True)
    try:
        tab = await b.get("data:text/html,<p>hello</p>")
        doc = await tab.send(cdp.dom.get_document(-1, True))
        print("html_from_tree:", repr(await util.html_from_tree(doc, tab)))
        print("get_content  :", repr(await tab.get_content()))
    finally:
        await b.stop()
asyncio.run(asyncio.wait_for(main(), 60))
