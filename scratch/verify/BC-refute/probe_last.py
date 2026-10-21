import asyncio, sys
sys.path.insert(0, "/tmp/claude-0/-home-user-zendriver/b2021b39-94e6-5220-9e66-7f33c0314a80/scratchpad/verify/BC-refute")
import zendriver as zd
from zendriver import cdp
from helper import PAGES, serve, desc
print("zendriver from", zd.__file__)
rows = "".join(f"<tr id='r{i}'><td>c{i}</td></tr>" for i in range(5))
PAGES["/main"] = f"<html><body><table>{rows}</table></body></html>"
async def main():
    srv, port = serve()
    browser = await zd.start(headless=True)
    try:
        tab = await browser.get(f"http://127.0.0.1:{port}/main")
        trs = await tab.select_all("tr")
        await asyncio.gather(*(r.query_selector("td") for r in trs))
        flags = [bool(getattr(r, "__last", None)) for r in trs]
        print("leftover flags", flags)
        for r, f in zip(trs, flags):
            await tab.send(cdp.dom.get_document(-1, True))  # make r's ids stale
            out = await tab.query_selector("td", r)
            print("  leftover" if f else "  clean   ", "->", desc(out))
    finally:
        await browser.stop(); srv.shutdown()
asyncio.run(asyncio.wait_for(main(), 60))
