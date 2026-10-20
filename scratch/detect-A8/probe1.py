import asyncio, pathlib, traceback, copy
import zendriver as zd
from zendriver import cdp

PAGE = pathlib.Path(__file__).parent / "page1.html"

async def step(name, coro):
    try:
        r = await asyncio.wait_for(coro, 15)
        print(f"[{name}] OK ->", repr(r)[:200])
        return r
    except Exception as e:
        print(f"[{name}] EXC {type(e).__name__}: {str(e)[:200]}")

async def main():
    browser = await zd.start(headless=True)
    try:
        tab = await browser.get(PAGE.as_uri())
        await tab.sleep(0.5)
        # A: click hidden
        hid = await tab.query_selector("#hid")
        await step("A click hidden", hid.click())
        print("  hidClicked =", await tab.evaluate("window.hidClicked"))
        # B: clear_input textarea
        ta = await tab.query_selector("#ta")
        await step("B clear_input textarea", ta.clear_input())
        print("  ta.value =", await tab.evaluate("document.getElementById('ta').value"))
        await step("B2 clear_input_by_deleting textarea", ta.clear_input_by_deleting())
        print("  ta.value =", await tab.evaluate("document.getElementById('ta').value"))
        inp = await tab.query_selector("#inp")
        await step("B3 clear_input input", inp.clear_input())
        print("  inp.value =", await tab.evaluate("document.getElementById('inp').value"))
        # C: apply swallowing
        await step("C apply throw", inp.apply("(e) => { throw new Error('boom') }"))
        await step("C2 apply reject", inp.apply("async (e) => { throw new Error('boom') }", await_promise=True))
        circ = await tab.query_selector("#circ")
        await step("C3 get_js_attributes circ", circ.get_js_attributes())
        # D: return_by_value=False
        r = await step("D apply rbv False", inp.apply("(e) => e.parentElement", return_by_value=False))
        if r is not None:
            print("  object_id =", getattr(r, "object_id", "n/a"), "type", type(r))
        # E: element.query_selector parent
        outer = await tab.query_selector("#outer")
        inner = await outer.query_selector("#inner")
        print("[E] inner type node:", type(inner.node).__name__, "tree type:", type(inner.tree).__name__)
        try:
            print("[E] inner.parent ->", inner.parent)
        except Exception as e:
            print("[E] inner.parent EXC", e)
        inner2 = await tab.query_selector("#inner")
        print("[E] inner2.parent (doc query) ->", repr(inner2.parent)[:80])
        bold = await outer.query_selector("#bold")
        print("[E] bold.parent ->", repr(bold.parent)[:80], " bold.parent.parent ->", repr(bold.parent.parent if bold.parent else None)[:80])
        # L: linked sources click
        links = await tab.get_all_linked_sources()
        lnk = [l for l in links if l.get("id") == "lnk"][0]
        print("[L] lnk tree:", lnk.tree)
        await step("L click 1", lnk.click())
        await step("L click 2", lnk.click())
        await step("L mouse_click", lnk.mouse_click())
        print("  lnkClicks =", await tab.evaluate("window.lnkClicks"))
        # I/J
        try:
            copy.copy(inner2); print("[I] copy ok")
        except RecursionError as e:
            print("[I] copy RecursionError")
        except Exception as e:
            print("[I] copy EXC", type(e).__name__, e)
        try:
            hash(inner2); print("[J] hash ok")
        except Exception as e:
            print("[J] hash EXC", type(e).__name__, e)
        # K: tree setter
        old = inner2.tree
        inner2.tree = None
        print("[K] after inner2.tree=None, tree is None?", inner2.tree is None, "attrs tree=", inner2.attrs.get("tree"))
        # G: save_to_dom
        cmt = await tab.query_selector("#cmt")
        cmt.attrs["data-x"] = "1"
        await step("G save_to_dom cmt", cmt.save_to_dom())
        print("  cmt outerHTML:", await tab.evaluate("document.getElementById('cmt').outerHTML"))
        print("  cmt innerText:", await tab.evaluate("document.getElementById('cmt').innerText"))
        esc = await tab.query_selector("#esc")
        esc.attrs["data-x"] = "1"
        await step("G2 save_to_dom esc", esc.save_to_dom())
        print("  esc outerHTML:", await tab.evaluate("document.getElementById('esc').outerHTML"))
        q = await tab.query_selector("#q")
        q.attrs["data-x"] = "1"
        await step("G3 save_to_dom q", q.save_to_dom())
        print("  q title:", await tab.evaluate("document.getElementById('q').title"))
    finally:
        await browser.stop()

asyncio.run(main())
