import asyncio, pathlib, traceback, time
import zendriver as zd

SITE = pathlib.Path(__file__).parent / "site"
def url(n): return (SITE / n).as_uri()

async def step(name, coro, t=20):
    t0 = time.monotonic()
    try:
        r = await asyncio.wait_for(coro, t)
        print(f"[{name}] OK in {time.monotonic()-t0:.2f}s ->", repr(r)[:300])
        return r
    except BaseException as e:
        print(f"[{name}] EXC in {time.monotonic()-t0:.2f}s -> {type(e).__name__}: {str(e)[:300]}")

async def main():
    browser = await zd.start(headless=True)
    try:
        tab = await browser.get(url("simple.html"))
        await asyncio.sleep(1)
        print("readyState:", await tab.evaluate("document.readyState"))
        await step("wait_for_ready_state default(interactive) on complete page", tab.wait_for_ready_state(timeout=3))
        await step("wait_for_ready_state loading on complete page", tab.wait_for_ready_state("loading", timeout=2))

        # tag_hint
        r = await step("find_elements_by_text tag_hint=a", tab.find_elements_by_text("needle", tag_hint="a"))
        if r: print("   tags:", [e.tag for e in r])

        # __call__
        await step("tab(text='Hello needle')", tab(text="Hello needle", timeout=2))
        await step("tab(selector='#p1')", tab(selector="#p1", timeout=2))
        await step("wait_for(text='Hello needle')", tab.wait_for(text="Hello needle", timeout=2))

        # evaluate unserializable
        for expr in ["1/0", "NaN", "-0", "10n", "undefined"]:
            await step(f"evaluate({expr})", tab.evaluate(expr))
        await step("evaluate(Promise.resolve(5)) no await", tab.evaluate("Promise.resolve(5)"))
        await step("evaluate(Promise.resolve(5), await)", tab.evaluate("Promise.resolve(5)", await_promise=True))
        await step("evaluate(Promise.reject(new Error('x')), await)", tab.evaluate("Promise.reject(new Error('x'))", await_promise=True))
        await step("evaluate(throw)", tab.evaluate("(()=>{throw new Error('boom')})()"))

        # iframe text
        tab = await browser.get(url("iframe_text.html"))
        await tab.wait_for_ready_state("complete")
        await asyncio.sleep(0.5)
        r = await step("iframe_text find_elements_by_text", tab.find_elements_by_text("inner needle"))
        if r: print("   ", [(e.tag, e.node_type, e.node_id, e.backend_node_id) for e in r])
        r = await step("iframe_text find_element_by_text", tab.find_element_by_text("inner needle"))
        if r: print("   ", (r.tag, r.node_type))

        tab = await browser.get(url("iframe_input.html"))
        await tab.wait_for_ready_state("complete")
        await asyncio.sleep(0.5)
        r = await step("iframe_input find_elements_by_text", tab.find_elements_by_text("needle"))
        if r: print("   ", [(e.tag, e.node_type) for e in r])
        await step("iframe_input find('inner needle')", tab.find("inner needle", timeout=2))
    finally:
        await browser.stop()

asyncio.run(main())
