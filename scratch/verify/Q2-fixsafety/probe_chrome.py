"""Real-Chromium probe: page blocked by alert() (or busy loop); time each polling method."""

import asyncio
import sys
import time

import zendriver
from zendriver.core import cloudflare

print("zendriver from", zendriver.__file__)

MODE = sys.argv[1] if len(sys.argv) > 1 else "alert"
OUTER = 8


async def run(name, coro_factory):
    tab = TAB
    t0 = time.monotonic()
    task = asyncio.ensure_future(coro_factory(tab))
    done, _ = await asyncio.wait({task}, timeout=OUTER)
    dt = time.monotonic() - t0
    if not done:
        frames = task.get_stack()
        where = (
            f"{frames[-1].f_code.co_name}:{frames[-1].f_lineno}" if frames else "?"
        )
        print(f"[{MODE}] {name}: STILL PENDING after {dt:.1f}s; innermost frame {where}")
        task.print_stack(limit=3, file=sys.stdout)
        task.cancel()
        try:
            await task
        except BaseException:
            pass
        return
    exc = task.exception()
    if exc is not None:
        print(f"[{MODE}] {name}: {type(exc).__name__}({exc}) after {dt:.2f}s")
    else:
        print(f"[{MODE}] {name}: returned {task.result()!r} after {dt:.2f}s")


async def main():
    global TAB
    browser = await zendriver.start(headless=True)
    try:
        tab = browser.main_tab
        TAB = tab
        await tab.get("data:text/html,<p id=topp>hi</p>")
        await tab.select("#topp", timeout=5)
        # sanity: unblocked
        await run("unblocked select('#nope', timeout=1)", lambda t: t.select("#nope", timeout=1))
        if MODE == "alert":
            await tab.evaluate("setTimeout(()=>alert('x'),200)", await_promise=False)
            await asyncio.sleep(1)
        cases = [
            ("select('#nope', timeout=1)", lambda t: t.select("#nope", timeout=1)),
            ("find('nope', timeout=1)", lambda t: t.find("nope", timeout=1)),
            ("find_all('nope', timeout=1)", lambda t: t.find_all("nope", timeout=1)),
            ("select_all('#nope', timeout=1)", lambda t: t.select_all("#nope", timeout=1)),
            ("wait_for(selector='#nope', timeout=1)", lambda t: t.wait_for(selector="#nope", timeout=1)),
            ("tab(selector='#nope', timeout=1)", lambda t: t(selector="#nope", timeout=1)),
            ("xpath('//nope', timeout=1)", lambda t: t.xpath("//nope", timeout=1)),
            ("cf_is_interactive_challenge_present(timeout=1)", lambda t: cloudflare.cf_is_interactive_challenge_present(t, timeout=1)),
            ("verify_cf(timeout=1)", lambda t: t.verify_cf(timeout=1)),
            ("wait_for_ready_state(timeout=1) [control]", lambda t: t.wait_for_ready_state("complete", timeout=1)),
        ]
        for name, f in cases:
            if MODE == "busy":
                # fresh 6 s busy period for each case
                await tab.evaluate(
                    "setTimeout(()=>{const e=Date.now()+6000; while(Date.now()<e){}},50)",
                    await_promise=False,
                )
                await asyncio.sleep(0.3)
            await run(name, f)
    finally:
        await browser.stop()


asyncio.run(main())
