import asyncio, sys, pathlib, os
import zendriver as zd
from zendriver import cdp
print("zendriver from", zd.__file__, sys.version.split()[0])
HERE = pathlib.Path(__file__).parent

async def run(label, coro, t=20):
    try:
        r = await asyncio.wait_for(coro, t)
        print(f"[{label}] OK -> {r!r}"[:300]); return r
    except Exception as e:
        print(f"[{label}] EXC {type(e).__name__}: {str(e)[:200]}")

async def main():
    browser = await zd.start(headless=True)
    try:
        tab = await browser.get((HERE / "page.html").as_uri())
        await tab.sleep(0.3)
        # R34 real-chrome get('class')
        plain = await tab.select("#plain")
        print("R34 get('class') ->", plain.get("class"), "| get('class_') ->", plain.get("class_"), "| keys", list(plain.attrs.keys()))
        # A8.10 save_to_dom
        for sel in ["#cmt", "#esc", "#q", "#plain"]:
            el = await tab.select(sel)
            el.attrs["data-x"] = "1"
            await run(f"save_to_dom {sel}", el.save_to_dom())
            print("   outerHTML:", await tab.evaluate(f"document.querySelector('{sel}').outerHTML"), "| innerText:", await tab.evaluate(f"document.querySelector('{sel}').innerText"))
        # A8.17 / A7.11 hashing
        links = await tab.select_all("a")
        await run("set(select_all('a'))", asyncio.sleep(0, set(links)) if False else _hash(lambda: set(links)))
        await run("hash(main_tab)", _hash(lambda: hash(browser.main_tab)))
        await run("set(browser.tabs)", _hash(lambda: set(browser.tabs)))
        t1 = browser.main_tab; before = (t1 == browser.tabs[0])
        # A6.9 evaluate unserializable
        for expr in ["1/0", "Math.max()", "NaN", "-0", "2n**64n", "10n", "0", "null", "undefined"]:
            await run(f"evaluate({expr})", tab.evaluate(expr))
        for expr in ["NaN", "10n"]:
            await run(f"evaluate({expr}, rbv=False)", tab.evaluate(expr, return_by_value=False))
        # A8.13 leak
        inp = await tab.select("#inp")
        first = await tab.send(cdp.dom.resolve_node(backend_node_id=inp.backend_node_id))
        await tab.send(cdp.heap_profiler.collect_garbage())
        h0 = await tab.send(cdp.runtime.get_heap_usage())
        N = 5000
        ids = set()
        for i in range(N):
            await inp.apply("(e) => 1")
            ids.add(str(inp._remote_object.object_id))
        await tab.send(cdp.heap_profiler.collect_garbage())
        h1 = await tab.send(cdp.runtime.get_heap_usage())
        alive = await run("first object id still alive", tab.send(cdp.runtime.call_function_on("function(){return this.id}", object_id=first.object_id, return_by_value=True)))
        print(f"   {N} apply -> {len(ids)} distinct ids; heap used {h0[0]/1e6:.2f}MB -> {h1[0]/1e6:.2f}MB (+{(h1[0]-h0[0])/N:.0f} B/call)")
        # navigation releases?
        await tab.reload(); await tab.sleep(0.5)
        await run("first object id after reload", tab.send(cdp.runtime.call_function_on("function(){return this.id}", object_id=first.object_id, return_by_value=True)))
    finally:
        await browser.stop()

async def _hash(fn):
    return fn()

asyncio.run(main())
