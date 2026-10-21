import asyncio
import sys
import traceback

sys.path.insert(0, __file__.rsplit("/", 1)[0])
from common import PAGES, serve, desc, step, browser_ctx, wait_loaded  # noqa
from zendriver import cdp
from zendriver.core.connection import ProtocolException

PAGES["/ph"] = (
    "<html><body><p>top</p>"
    "<iframe id='f1' srcdoc=\"<input placeholder='Search needle'>\"></iframe>"
    "</body></html>"
)
PAGES["/shadowhost"] = (
    "<html><body><p>top</p><iframe id='f2' src='/shadowinner'></iframe></body></html>"
)
PAGES["/shadowinner"] = (
    "<html><body><div id='host'></div>"
    "<script>document.getElementById('host').attachShadow({mode:'open'}).innerHTML='<b>shadow needle</b>';</script>"
    "</body></html>"
)
PAGES["/cross"] = lambda port: (
    f"<html><body><iframe id='child-frame' src='http://localhost:{port}/child'></iframe></body></html>"
)
PAGES["/child"] = "<html><body><p id='child'>hello from iframe</p></body></html>"
PAGES["/box"] = (
    "<html><body><div id='box'><span>a</span></div>"
    "<div id='outer'><div id='inner'>in</div><p id='deep'><b id='bold'>B</b></p></div></body></html>"
)


async def main():
    srv = serve()
    port = srv.server_address[1]
    base = f"http://127.0.0.1:{port}"
    async with browser_ctx() as browser:
        print("\n=== A6.2 placeholder in srcdoc iframe")
        tab = await browser.get(base + "/ph")
        print("loaded:", await wait_loaded(tab, "!!(document.getElementById('f1').contentDocument && document.getElementById('f1').contentDocument.querySelector('input'))", True))
        r = await step("find_elements_by_text('needle')", tab.find_elements_by_text("needle"))
        if isinstance(r, Exception):
            traceback.print_exception(r, limit=-3)
        await step("find('needle')", tab.find("needle", timeout=2))
        await step("find_all('needle')", tab.find_all("needle", timeout=2))
        await step("wait_for(text='needle')", tab.wait_for(text="needle", timeout=2))
        # control: placeholder in top-level doc
        await tab.evaluate("document.body.insertAdjacentHTML('beforeend', \"<input placeholder='top needle2'>\")")
        r = await step("control top-level find_elements_by_text('needle2')", tab.find_elements_by_text("needle2"))

        print("\n=== A6.2 open shadow root in same-origin iframe")
        tab = await browser.get(base + "/shadowhost")
        print("loaded:", await wait_loaded(tab, "!!(document.getElementById('f2').contentDocument && document.getElementById('f2').contentDocument.getElementById('host') && document.getElementById('f2').contentDocument.getElementById('host').shadowRoot)", True))
        await step("find('shadow needle')", tab.find("shadow needle", timeout=2))
        await step("find_all('shadow needle')", tab.find_all("shadow needle", timeout=2))

        print("\n=== A5.3 cross-origin iframe query_selector")
        tab = await browser.get(base + "/cross")
        await asyncio.sleep(1.5)
        iframe = await tab.select("#child-frame")
        print("cross content_document:", iframe.content_document)
        print("get_frames:", await tab.get_frames())
        await step("iframe.query_selector_all('p')", iframe.query_selector_all("p"))
        r = await step("iframe.query_selector('p')", iframe.query_selector("p"))
        if isinstance(r, Exception):
            traceback.print_exception(r, limit=-3)

        print("\n=== A5.8/B15.7 invalid selector, element-scoped vs tab-level")
        tab = await browser.get(base + "/box")
        await wait_loaded(tab)
        box = await tab.select("#box")
        await step("tab.query_selector_all('span[[')", tab.query_selector_all("span[["))
        await step("tab.query_selector('span[[')", tab.query_selector("span[["))
        await step("box.query_selector_all('span[[')", box.query_selector_all("span[["))
        await step("box.query_selector('span[[')", box.query_selector("span[["))
        await step("box.query_selector_all('a[[')", box.query_selector_all("a[["))
        # show directly what DOM error is produced for element-scoped invalid selector
        try:
            await box.update()
            await tab.send(cdp.dom.query_selector_all(box.node_id, "span[["))
        except ProtocolException as e:
            print("direct elem-scoped DOM.querySelectorAll invalid ->", e.message)

        print("\n=== A8.8 element-scoped query result .parent / .node")
        outer = await tab.select("#outer")
        inner = await outer.query_selector("#inner")
        print("inner:", desc(inner), "type(inner.node):", type(inner.node).__name__, "type(inner.tree):", type(inner.tree).__name__)
        print("inner.parent:", desc(inner.parent))
        inner_doc = await tab.query_selector("#inner")
        print("tab-level inner.parent:", desc(inner_doc.parent))
        bold = await outer.query_selector("#bold")
        print("bold.parent:", desc(bold.parent), "bold.parent.parent:", desc(bold.parent.parent) if bold.parent else 'n/a')
    srv.shutdown()


asyncio.run(asyncio.wait_for(main(), 100))
