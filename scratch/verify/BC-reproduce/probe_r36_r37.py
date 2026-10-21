import asyncio
import contextlib
import io
import sys

sys.path.insert(0, __file__.rsplit("/", 1)[0])
from common import PAGES, serve, desc, step, browser_ctx, wait_loaded  # noqa
from zendriver import cdp
from zendriver.core.connection import ProtocolException

PAGES["/text"] = (
    "<html><body>"
    "<button title='Login'>Login</button>"
    "<p id='p2'>needle <b>x</b> needle</p>"
    "<p id='p1'>Hello hint world</p><a href='#'>hint link</a>"
    "<p id='topp'>top paragraph</p>"
    "</body></html>"
)
PAGES["/frames"] = (
    "<html><body><div id='top'>t</div><iframe id='fr' src='/inner'></iframe></body></html>"
)
PAGES["/inner"] = "<html><body><div id='inner'>i</div></body></html>"
PAGES["/table"] = (
    "<html><body><p id='topp'>p</p><p>q</p><table>"
    + "".join(f"<tr id='r{i}'><td>c{i}</td></tr>" for i in range(20))
    + "</table></body></html>"
)


class Tee(io.TextIOBase):
    def __init__(self, real):
        self.real = real
        self.buf = []

    def write(self, s):
        self.buf.append(s)
        return self.real.write(s)


async def main():
    srv = serve()
    port = srv.server_address[1]
    base = f"http://127.0.0.1:{port}"
    async with browser_ctx() as browser:
        tab = await browser.get(base + "/text")
        await wait_loaded(tab)
        print("\n=== A6.4 duplicates")
        r = await tab.find_all("Login", timeout=3)
        print("find_all('Login'):", [(e.tag, e.backend_node_id) for e in r])
        r = await tab.find_all("needle", timeout=3)
        print("find_all('needle'):", [(e.tag, e.backend_node_id) for e in r])

        print("\n=== A6.10 tag_hint")
        r = await tab.find_elements_by_text("hint", tag_hint="a")
        print("find_elements_by_text('hint', tag_hint='a') tags:", [e.tag for e in r])

        print("\n=== A5.10/A6.11 return_enclosing_element")
        r = await tab.find("top paragraph", return_enclosing_element=False, timeout=3)
        print("find(..., return_enclosing_element=False):", desc(r))
        r = await tab.find("top paragraph", best_match=False, return_enclosing_element=False, timeout=3)
        print("find(..., best_match=False, return_enclosing_element=False):", desc(r))
        r = await tab.find_element_by_text("top paragraph", return_enclosing_element=False)
        print("find_element_by_text(..., return_enclosing_element=False):", desc(r))

        print("\n=== A5.6 select_all include_frames partial results")
        tab = await browser.get(base + "/frames")
        await wait_loaded(tab, "!!(document.getElementById('fr').contentDocument && document.getElementById('fr').contentDocument.getElementById('inner'))", True)
        seq = await tab.select_all("div", include_frames=True)
        print("sequential:", [e.attrs.get("id") for e in seq])
        real = sys.stdout
        tee = Tee(real)
        sys.stdout = tee
        try:
            for attempt in range(3):
                res = await asyncio.wait_for(asyncio.gather(*(tab.select_all("div", include_frames=True, timeout=3) for _ in range(6))), 30)
                print(f"attempt {attempt} lens:", [len(x) for x in res], "ids:", [[e.attrs.get('id') for e in x] for x in res])
        finally:
            sys.stdout = real
        printed = "".join(tee.buf)
        print("'Exception in new content doc ids loop' printed count:", printed.count("Exception in new content doc ids loop"))

        # path (2): main doc stale -> retry with _node=doc drops content_doc_nodes. Force: patch tab.send once
        print("\n--- A5.6 path(2): force stale main-doc query once")
        orig_send = tab.send
        state = {"n": 0}

        async def send(cmd, *a, **k):
            # intercept the first DOM.querySelectorAll after getDocument: perform an extra getDocument first, making doc ids stale
            gen = cmd
            res = None
            return await orig_send(cmd, *a, **k)

        # use a simpler approach: interleave a getDocument right after the main getDocument returns
        async def send2(cmd, *a, **k):
            r = await orig_send(cmd, *a, **k)
            # detect the get_document generator by result type
            if isinstance(r, cdp.dom.Node) and state["n"] == 0:
                state["n"] = 1
                await orig_send(cdp.dom.get_document(-1, True))  # invalidates r's node ids
            return r

        tab.send = send2
        try:
            r = await step("query_selector_all('div', _include_frames=True) with stale main doc", tab.query_selector_all("div", _include_frames=True))
            if isinstance(r, list):
                print("  ids:", [e.attrs.get("id") for e in r])
        finally:
            del tab.send
        r = await tab.query_selector_all("div", _include_frames=True)
        print("  control (no stale):", [e.attrs.get("id") for e in r])

        print("\n=== A5.2 concurrent DOM queries")
        tab = await browser.get(base + "/table")
        await wait_loaded(tab)
        rows = await tab.select_all("tr")
        print("rows:", len(rows))
        for attempt in range(3):
            res = await asyncio.wait_for(asyncio.gather(*(r.query_selector("td") for r in rows)), 60)
            last = sum(1 for r in rows if r.__dict__.get("__last"))
            print(f"attempt {attempt}: row.query_selector None count {sum(1 for x in res if x is None)} of {len(res)}; __last leftovers {last}")
        res = await asyncio.wait_for(asyncio.gather(*(r.query_selector_all("td") for r in rows)), 60)
        print("row.query_selector_all empty count:", sum(1 for x in res if not x), "of", len(res))
        res = await asyncio.wait_for(asyncio.gather(*(tab.query_selector("#topp") for _ in range(10))), 60)
        print("10x tab.query_selector('#topp') None count:", sum(1 for x in res if x is None))
        res = await asyncio.wait_for(asyncio.gather(*(tab.query_selector_all("p") for _ in range(10))), 60)
        print("10x tab.query_selector_all('p') lens:", [len(x) for x in res])
        # sequential control
        res = [await r.query_selector("td") for r in rows]
        print("sequential row.query_selector None count:", sum(1 for x in res if x is None))
        # __last leftover effect: take a row with __last set, cause one stale failure, see it give up without retry
        leftovers = [r for r in rows if r.__dict__.get("__last")]
        print("rows with __last leftover now:", len(leftovers))
        if leftovers:
            r0 = leftovers[0]
            calls = []
            orig_update = r0.update

            async def upd(*a, **k):
                calls.append(1)
                return await orig_update(*a, **k)

            object.__setattr__(r0, "update", upd)
            # make r0's node id stale by fetching a new document, then call tab.query_selector with _node=r0 directly (skips Element.update)
            await tab.send(cdp.dom.get_document(-1, True))
            out = await tab.query_selector("td", r0)
            print("stale leftover-row tab.query_selector('td', row) ->", out, "update() calls in retry:", len(calls))
            # control: a row without __last
            r1 = [r for r in rows if not r.__dict__.get("__last")][0]
            await tab.send(cdp.dom.get_document(-1, True))
            out = await tab.query_selector("td", r1)
            print("stale normal-row tab.query_selector('td', row) ->", desc(out))
    srv.shutdown()


asyncio.run(asyncio.wait_for(main(), 110))
