import asyncio, pathlib, traceback, time, sys
import zendriver as zd
from zendriver import cdp
SITE = pathlib.Path(__file__).parent / "site"
def url(n): return (SITE / n).as_uri()
async def step(name, coro, t=30):
    t0 = time.monotonic()
    try:
        r = await asyncio.wait_for(coro, t)
        print(f"[{name}] OK in {time.monotonic()-t0:.2f}s ->", repr(r)[:200]); return r
    except BaseException as e:
        print(f"[{name}] EXC in {time.monotonic()-t0:.2f}s -> {type(e).__name__}: {str(e)[:200]}")
async def main():
    browser = await zd.start(headless=True)
    try:
        tab = await browser.get(url("long.html"))
        await tab.wait_for_ready_state("complete")
        t2 = await browser.get(url("simple.html"), new_tab=True)
        await step("activate main", tab.activate())
        await step("bring_to_front t2", t2.bring_to_front())
        await step("scroll_down", tab.scroll_down(50))
        print("scrollY", await tab.evaluate("window.scrollY"))
        await step("scroll_up", tab.scroll_up(50))
        print("scrollY", await tab.evaluate("window.scrollY"))
        await step("js_dumps(navigator) keys", tab.js_dumps("navigator"))
        r = await step("js_dumps(location, False)", tab.js_dumps("location", return_by_value=False))
        await step("get_content", tab.get_content())
        await tab.get(url("simple.html"))
        await tab.wait_for_ready_state("complete")
        await step("back", tab.back()); await asyncio.sleep(1)
        print("url", await tab.evaluate("location.href"))
        await step("forward", tab.forward()); await asyncio.sleep(1)
        print("url", await tab.evaluate("location.href"))
        await step("evaluate NaN by ref", tab.evaluate("NaN", return_by_value=False))
        await step("evaluate 10n by ref", tab.evaluate("10n", return_by_value=False))
        await step("evaluate Promise by ref no await", tab.evaluate("Promise.resolve(5)", return_by_value=False))
    finally:
        await browser.stop()
asyncio.run(main())
