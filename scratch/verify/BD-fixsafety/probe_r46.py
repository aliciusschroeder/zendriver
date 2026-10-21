import asyncio, os, sys
import zendriver
from zendriver import cdp
print("zendriver from", zendriver.__file__)
D = sys.argv[1]
async def run(label, coro):
    try:
        r = await asyncio.wait_for(coro, 15)
        print(f"[{label}] OK ->", repr(r)[:200])
        return r
    except Exception as e:
        print(f"[{label}] EXC {type(e).__name__}: {str(e)[:200]}")
async def main():
    browser = await zendriver.start(headless=True)
    try:
        tab = await browser.get(f"file://{D}/page_r46.html")
        await tab.sleep(0.3)
        # A8.10
        for sel in ("#cmt", "#esc", "#q"):
            el = await tab.select(sel)
            el.attrs["data-x"] = "1"
            await run(f"save_to_dom {sel}", el.save_to_dom())
            html = await tab.evaluate(f"(document.querySelector('[id={sel[1:]}]')||{{}}).outerHTML")
            txt = await tab.evaluate(f"(document.querySelector('[id={sel[1:]}]')||{{}}).innerText")
            print("   outerHTML:", html, "| innerText:", repr(txt))
        # A6.9
        for expr in ("1/0", "Math.max()", "NaN", "-0", "10n"):
            await run(f"evaluate({expr})", tab.evaluate(expr))
        # A8.17 / A7.11
        inp = await tab.select("#inp")
        try: print("hash(el)", hash(inp))
        except TypeError as e: print("hash(el) TypeError", e)
        try: print("hash(tab)", hash(tab))
        except TypeError as e: print("hash(tab) TypeError", e)
        # A8.13: resolveNode handles never released
        first = None; ids = set()
        for i in range(500):
            await inp.apply("(e) => 1")
            ids.add(inp._remote_object.object_id)
            if first is None: first = inp._remote_object.object_id
        r, exc = await tab.send(cdp.runtime.call_function_on("function(){return this.id}", object_id=first, return_by_value=True))
        print(f"[A8.13] 500 applies -> {len(ids)} distinct object ids; first id still resolves: value={r.value!r} exc={exc is not None}")
        # count objects via heap? use Runtime.getProperties of first to show it's alive
        pid = browser._process_pid
    finally:
        await browser.stop()
    # B16.10
    async with await zendriver.start(headless=True) as b:
        pid = b._process_pid
    await asyncio.sleep(1)
    alive = os.path.exists(f"/proc/{pid}") and open(f"/proc/{pid}/stat").read().split()[2] != 'Z'
    print(f"[B16.10] after `async with`: stopped={b.stopped} pid {pid} alive={alive}")
    await b.stop()
    await asyncio.sleep(1)
    alive = os.path.exists(f"/proc/{pid}") and open(f"/proc/{pid}/stat").read().split()[2] != 'Z'
    print(f"[B16.10] after explicit stop: alive={alive}")
asyncio.run(main())
