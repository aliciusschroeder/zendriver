import asyncio
import contextlib
import io
import sys
import time

sys.path.insert(0, "/tmp/claude-0/-home-user-zendriver/b2021b39-94e6-5220-9e66-7f33c0314a80/scratchpad/verify/BC-refute")
import zendriver as zd
from helper import PAGES, serve, desc

print("zendriver from", zd.__file__, "python", sys.version.split()[0])


def slow_inner(handler):
    time.sleep(0.05 * (hash(handler.path) % 8))
    return "<html><body><div id='inner'>inner</div></body></html>"


PAGES["/fr"] = "<html><body><div id='top'>top</div><iframe id='fr' src='/inner'></iframe><iframe src='/inner?b'></iframe></body></html>"
PAGES["/inner"] = slow_inner


async def main():
    srv, port = serve()
    browser = await zd.start(headless=True)
    prints = 0
    partial = 0
    try:
        for i in range(15):
            tab = await browser.get(f"http://127.0.0.1:{port}/fr?{i}")
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                r1 = await tab.select("#inner", include_frames=True, timeout=5)
                r2 = await tab.select_all("div", include_frames=True, timeout=5)
            out = buf.getvalue()
            prints += out.count("Exception in new content doc ids loop")
            if len(r2) < 3:
                partial += 1
            print(f"  [{i}] select->{desc(r1)} select_all lens={len(r2)} prints={out.count('Exception in new content')}")
    finally:
        await browser.stop()
        srv.shutdown()
    print("total prints", prints, "partial select_all", partial)


asyncio.run(asyncio.wait_for(main(), 100))
