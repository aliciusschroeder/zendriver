import asyncio, sys
sys.path.insert(0, __file__.rsplit("/", 1)[0])
import zendriver as zd
from probe_common import serve
print("zendriver from", zd.__file__)
async def main():
    srv, port = serve()
    b = await zd.start(headless=True)
    try:
        tab = await b.get(f"http://127.0.0.1:{port}/text")
        p = await tab.select("#topp")
        t = p.children[0]
        print("text child:", t.node_name, t.node_type)
        for m in ("query_selector_all", "query_selector"):
            try:
                print(m, "->", await asyncio.wait_for(getattr(t, m)("b"), 20))
            except Exception as e:
                print(m, "EXC", type(e).__name__, str(e).splitlines()[0])
    finally:
        await b.stop(); srv.shutdown()
asyncio.run(main())
