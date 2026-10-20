import asyncio, pathlib, traceback, time, sys
import zendriver as zd
from zendriver import cdp
SITE = pathlib.Path(__file__).parent / "site"
def url(n): return (SITE / n).as_uri()
async def step(name, coro, t=20):
    t0 = time.monotonic()
    try:
        r = await asyncio.wait_for(coro, t)
        print(f"[{name}] OK in {time.monotonic()-t0:.2f}s ->", repr(r)[:300]); return r
    except BaseException as e:
        print(f"[{name}] EXC in {time.monotonic()-t0:.2f}s -> {type(e).__name__}: {str(e)[:300]}")
async def win(tab, label):
    wid, b = await tab.get_window()
    print(f"   {label}: state={b.window_state} l={b.left} t={b.top} w={b.width} h={b.height}")
async def main():
    headless = sys.argv[1] == "1"
    browser = await zd.start(headless=headless, sandbox=False, browser_connection_max_tries=120, browser_connection_timeout=0.5, browser_args=["--disable-gpu","--disable-dev-shm-usage"])
    try:
        tab = await browser.get(url("simple.html"))
        await win(tab, "initial")
        await step("set_window_size(10,20,800,600)", tab.set_window_size(10, 20, 800, 600)); await win(tab, "after size")
        await step("maximize", tab.maximize()); await win(tab, "after max")
        await step("maximize again", tab.maximize()); await win(tab, "after max2")
        await step("set_window_size(10,20,900,700) while max", tab.set_window_size(10, 20, 900, 700)); await win(tab, "after size2")
        await step("maximize", tab.maximize()); await win(tab, "after max3")
        await step("medimize", tab.medimize()); await win(tab, "after medimize")
        await step("set_window_size(10,20,800,600)", tab.set_window_size(10, 20, 800, 600)); await win(tab, "after size3")
        await step("minimize", tab.minimize()); await win(tab, "after min")
        await step("medimize", tab.medimize()); await win(tab, "after medimize2")
        await step("fullscreen", tab.fullscreen()); await win(tab, "after full")
        await step("minimize from full", tab.minimize()); await win(tab, "after min from full")
        await step("set_window_state('')", tab.set_window_state(state="")); await win(tab, "after empty state")
    finally:
        await browser.stop()
asyncio.run(main())
