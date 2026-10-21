import asyncio
import sys

sys.path.insert(0, "/tmp/claude-0/-home-user-zendriver/b2021b39-94e6-5220-9e66-7f33c0314a80/scratchpad/verify/BC-refute")
import zendriver as zd
from helper import PAGES, serve

print("zendriver from", zd.__file__, "python", sys.version.split()[0])
rows = "".join(f"<tr id='r{i}'><td>c{i}</td></tr>" for i in range(20))
PAGES["/main"] = f"""<html><body><p id="topp">top paragraph</p><table>{rows}</table></body></html>"""


async def main():
    srv, port = serve()
    browser = await zd.start(headless=True)
    try:
        tab = await browser.get(f"http://127.0.0.1:{port}/main")
        await tab.sleep(1.0)
        for n in (2, 3, 4, 5, 10):
            nones = []
            for _ in range(5):
                res = await asyncio.gather(*(tab.query_selector("#topp") for _ in range(n)))
                nones.append(sum(x is None for x in res))
            enones = []
            for _ in range(5):
                trs = (await tab.select_all("tr"))[:n]
                res = await asyncio.gather(*(r.query_selector("td") for r in trs))
                enones.append(sum(x is None for x in res))
            print(f"   n={n}: tab.query_selector None counts {nones}; row.query_selector None counts {enones}")
    finally:
        await browser.stop()
        srv.shutdown()


asyncio.run(asyncio.wait_for(main(), 100))
