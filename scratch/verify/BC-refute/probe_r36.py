import asyncio
import pathlib
import sys

sys.path.insert(0, "/tmp/claude-0/-home-user-zendriver/b2021b39-94e6-5220-9e66-7f33c0314a80/scratchpad/verify/BC-refute")
import zendriver as zd
from zendriver import cdp
from helper import PAGES, serve, show, desc

print("zendriver from", zd.__file__, "python", sys.version.split()[0])

PAGES["/main"] = """<html><body>
<button title="Login">Login</button>
<p id="p2">needleA <b>x</b> needleA</p>
<p id="p1">Hello needleB world</p><a href="#">needleB link</a>
<p id="topp">top paragraph</p>
</body></html>"""
PAGES["/fr"] = """<html><body><div id="top">top</div><iframe id="fr" src="/inner"></iframe></body></html>"""
PAGES["/inner"] = """<html><body><div id="inner">inner</div></body></html>"""


async def main():
    srv, port = serve()
    browser = await zd.start(headless=True)
    try:
        base = f"http://127.0.0.1:{port}"
        tab = await browser.get(base + "/main")
        await tab.sleep(1.0)
        print("=== A6.4 duplicates")
        await tab.send(cdp.dom.get_document(-1, True))
        sid, n = await tab.send(cdp.dom.perform_search("Login", True))
        ids = await tab.send(cdp.dom.get_search_results(sid, 0, n))
        for i in ids:
            d = await tab.send(cdp.dom.describe_node(node_id=i))
            print("   performSearch Login hit:", d.node_name, d.node_type)
        r = await tab.find_all("Login", timeout=2)
        print("find_all Login:", desc(r))
        r = await tab.find_all("needleA", timeout=2)
        print("find_all needleA:", desc(r))

        print("\n=== A6.10 tag_hint")
        r = await tab.find_elements_by_text("needleB", tag_hint="a")
        print("find_elements_by_text(needleB, tag_hint=a):", [e.tag for e in r])

        print("\n=== A5.10/A6.11 return_enclosing_element")
        for flag in (True, False):
            for bm in (True, False):
                r = await tab.find("top paragraph", best_match=bm, return_enclosing_element=flag, timeout=2)
                print(f"   find(return_enclosing_element={flag}, best_match={bm}):", desc(r))

        print("\n=== groceries sample find_all('Apples')")
        sample = pathlib.Path("/home/user/zendriver/tests/sample_data/groceries.html").as_uri()
        tab = await browser.get(sample)
        await tab.sleep(0.5)
        r = await tab.find_all("Apples", timeout=2)
        print("   ", desc(r))
        f = await tab.find("Apples")
        print("   find Apples:", desc(f))

        print("\n=== A5.6 include_frames: sequential and right after load")
        for attempt in range(3):
            tab = await browser.get(base + "/fr")
            r = await tab.select("#inner", include_frames=True, timeout=5)
            print("   select #inner right after load:", desc(r))
        await tab.sleep(1.0)
        r = await tab.select_all("div", include_frames=True)
        print("   sequential select_all div:", desc(r))
        res = await asyncio.gather(*(tab.select_all("div", include_frames=True) for _ in range(6)))
        print("   concurrent lens:", [len(x) for x in res])
    finally:
        await browser.stop()
        srv.shutdown()


asyncio.run(asyncio.wait_for(main(), 100))
