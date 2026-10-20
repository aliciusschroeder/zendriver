import asyncio, pathlib
import zendriver as zd
from zendriver import cdp
PAGE = pathlib.Path(__file__).parent / "page3.html"
async def main():
    browser = await zd.start(headless=True)
    try:
        tab = await browser.get(PAGE.as_uri())
        await tab.sleep(1.0)
        iframe = await tab.query_selector("#fr")
        inner = await iframe.query_selector("#x")
        print("inner:", inner, " parent before update:", repr(inner.parent)[:60])
        await tab.evaluate("document.getElementById('fr').contentDocument.getElementById('x').setAttribute('data-v','2')")
        await inner.update()
        print("after JS set data-v=2 and update(): inner.get('data-v') =", inner.get("data-v"))
        print("parent after update:", repr(inner.parent)[:60])
        await inner.remove_from_dom()
        print("still in iframe after remove_from_dom():", await tab.evaluate("!!document.getElementById('fr').contentDocument.getElementById('x')"))
        # compare with main doc element
        m = await tab.query_selector("#main")
        await m.remove_from_dom()
        print("main removed:", not await tab.evaluate("!!document.getElementById('main')"))
        # text search path
        y = await tab.find_element_by_text("yy")
        print("find yy ->", y, "tree is iframe doc?", y.tree is not None and y.tree.node_name)
        await y.remove_from_dom()
        print("yy still in iframe after remove_from_dom():", await tab.evaluate("!!document.getElementById('fr').contentDocument.getElementById('y')"))
    finally:
        await asyncio.wait_for(browser.stop(), 20)
asyncio.run(main())
