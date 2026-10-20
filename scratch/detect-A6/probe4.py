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
        tab = await browser.get(url("iframe_src.html"))
        await tab.wait_for_ready_state("complete"); await asyncio.sleep(0.5)
        el = await step("wait_for(text='inner needle')", tab.wait_for(text="inner needle", timeout=2))
        if el is not None:
            print("   node_type", el.node_type, "tag", el.tag)
            await step("click on returned element", el.click(), 10)
        # busy page
        tab = await browser.get(url("busy.html"))
        await asyncio.sleep(1.0)
        await step("busy: wait_for(selector='#nope', timeout=2)", tab.wait_for(selector="#nope", timeout=2))
        await asyncio.sleep(1)
        tab = await browser.get(url("alert.html"))
        await asyncio.sleep(1.0)
        await step("alert: wait_for(selector='#nope', timeout=2)", tab.wait_for(selector="#nope", timeout=2), 15)
        await step("alert: wait_for(text='zzz', timeout=2)", tab.wait_for(text="zzzqq", timeout=2), 15)
    finally:
        await browser.stop()
asyncio.run(main())
