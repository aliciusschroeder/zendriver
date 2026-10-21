import asyncio, sys
sys.path.insert(0, __file__.rsplit("/", 1)[0])
import zendriver as zd
from probe_common import serve, PAGES
print("zendriver from", zd.__file__)
PAGES["/tc"] = """<!doctype html><html><body><div id="w"><iframe srcdoc="<p>inside</p>"></iframe>tail</div>
<div id="w2"><iframe srcdoc="<p>nested <iframe srcdoc='<b>deepest needle</b>'></iframe></p>"></iframe></div></body></html>"""
async def main():
    srv, port = serve()
    b = await zd.start(headless=True)
    try:
        tab = await b.get(f"http://127.0.0.1:{port}/tc")
        await tab.wait_for_ready_state("complete"); await asyncio.sleep(1)
        w = await tab.select("#w")
        print("w.text:", repr(w.text), "w.text_all:", repr(w.text_all))
        r = await tab.find_all("deepest needle")
        print("find_all deepest:", [(e.node_name, e.backend_node_id) for e in r])
        el = await tab.find("deepest needle", best_match=True)
        print("find deepest:", el.node_name, el.node_type, "parent:", el.parent)
    finally:
        await b.stop(); srv.shutdown()
asyncio.run(main())
