import asyncio, pathlib, traceback, time, sys
import zendriver as zd
from zendriver import cdp
SITE = pathlib.Path(__file__).parent / "site"
def url(n): return (SITE / n).as_uri()
async def run(name, coro, t):
    task = asyncio.create_task(coro)
    done, _ = await asyncio.wait({task}, timeout=t)
    if not done:
        print(f"[{name}] STILL RUNNING after {t}s; stack:")
        task.print_stack(file=sys.stdout)
        task.cancel()
        try: await task
        except BaseException as e: print("   cancelled ->", type(e).__name__)
    else:
        try: print(f"[{name}] done ->", repr(task.result())[:200])
        except BaseException as e: print(f"[{name}] EXC -> {type(e).__name__}: {e}")
async def main():
    browser = await zd.start(headless=True)
    try:
        tab = await browser.get(url("alert.html"))
        await asyncio.sleep(1.0)
        await run("alert wait_for selector", tab.wait_for(selector="#nope", timeout=2), 8)
        await run("alert query_selector", tab.query_selector("#nope"), 5)
        await run("alert get_content", tab.get_content(), 5)
        await run("alert find_elements_by_text", tab.find_elements_by_text("zzzq"), 5)
        await run("alert sleep", tab.sleep(0.1), 5)
        await run("alert is_scrolled_to_bottom", tab.is_scrolled_to_bottom(), 5)
        await run("alert get_window", tab.get_window(), 5)
        await run("alert reload", tab.reload(), 5)
    finally:
        await browser.stop()
asyncio.run(main())
