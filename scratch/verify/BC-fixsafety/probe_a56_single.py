import asyncio, contextlib, io, sys
sys.path.insert(0, __file__.rsplit("/", 1)[0])
import zendriver as zd
from probe_common import serve
print("zendriver from", zd.__file__)
async def main():
    srv, port = serve()
    b = await zd.start(headless=True)
    try:
        hits = 0; partial = 0
        for i in range(8):
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                tab = await b.get(f"http://127.0.0.1:{port}/main?{i}")
                r = await asyncio.wait_for(tab.select_all("div", include_frames=True), 20)
            hits += "Exception in new content doc ids loop" in buf.getvalue()
            partial += len(r) < 6
        print("single-call after load: print seen", hits, "of 8; partial results", partial, "of 8")
    finally:
        await b.stop(); srv.shutdown()
asyncio.run(main())
