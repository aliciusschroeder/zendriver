import asyncio
import sys

sys.path.insert(0, __file__.rsplit("/", 1)[0])
from common import PAGES, serve, desc, step, browser_ctx, wait_loaded  # noqa
from zendriver import cdp
from zendriver.core.connection import ProtocolException

PAGES["/frames"] = (
    "<html><body><div id='top'>t</div><iframe id='fr' src='/inner'></iframe></body></html>"
)
PAGES["/inner"] = "<html><body><div id='inner'><span>a</span><b>b</b></div></body></html>"


async def main():
    srv = serve()
    port = srv.server_address[1]
    base = f"http://127.0.0.1:{port}"
    async with browser_ctx() as browser:
        tab = browser.main_tab
        for i in range(4):
            await tab.get(base + f"/frames?{i}")
            r = await step(f"immediate select('#inner', include_frames=True) #{i}", tab.select("#inner", include_frames=True, timeout=5))
        print("\n=== A5.4 mechanism")
        await wait_loaded(tab, "!!(document.getElementById('fr').contentDocument && document.getElementById('fr').contentDocument.getElementById('inner'))", True)
        inner = await tab.select("#inner", include_frames=True)
        nid = inner.node_id
        ids = await tab.send(cdp.dom.query_selector_all(nid, "b"))
        print("direct DOM.querySelectorAll(inner.node_id,'b') before update:", ids)
        await inner.update()
        print("node_id before/after update:", nid, inner.node_id, "tree:", inner.tree.node_name)
        try:
            await tab.send(cdp.dom.query_selector_all(inner.node_id, "b"))
        except ProtocolException as e:
            print("direct DOM.querySelectorAll after update ->", e.message)
    srv.shutdown()


asyncio.run(asyncio.wait_for(main(), 100))
