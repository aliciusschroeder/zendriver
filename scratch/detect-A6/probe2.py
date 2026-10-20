import asyncio, pathlib, traceback, time
import zendriver as zd
SITE = pathlib.Path(__file__).parent / "site"
def url(n): return (SITE / n).as_uri()
async def step(name, coro, t=20):
    t0 = time.monotonic()
    try:
        r = await asyncio.wait_for(coro, t)
        print(f"[{name}] OK in {time.monotonic()-t0:.2f}s ->", repr(r)[:300]); return r
    except BaseException as e:
        print(f"[{name}] EXC in {time.monotonic()-t0:.2f}s -> {type(e).__name__}: {str(e)[:300]}")
async def main():
    browser = await zd.start(headless=True)
    try:
        tab = await browser.get(url("iframe_src.html"))
        await tab.wait_for_ready_state("complete"); await asyncio.sleep(0.5)
        r = await step("find_elements_by_text inner needle", tab.find_elements_by_text("inner needle"))
        if r: print("   ", [(e.tag, e.node_type) for e in r])
        r = await step("find_element_by_text inner needle", tab.find_element_by_text("inner needle"))
        if r: print("   ", (r.tag, r.node_type))
        await step("find(best_match=False)", tab.find("inner needle", best_match=False, timeout=2))
        await step("find_all(shadow needle)", tab.find_all("shadow needle", timeout=2))
        await step("find(shadow needle)", tab.find("shadow needle", timeout=2))
        tab = await browser.get(url("iframe_input.html"))
        await tab.wait_for_ready_state("complete"); await asyncio.sleep(0.5)
        await step("iframe_input find('needle')", tab.find("needle", timeout=2))
        await step("iframe_input find_all('needle')", tab.find_all("needle", timeout=2))
        await step("iframe_input find('outer')", tab.find("outer", timeout=2))
        await step("iframe_input wait_for(text='outer')", tab.wait_for(text="outer", timeout=2))
    finally:
        await browser.stop()
asyncio.run(main())
