"""B14.5 (real headless Chromium): tab.wait() / await tab while busy, then the tab goes away."""

import asyncio
import sys

import zendriver
from zendriver import cdp

print("zendriver from", zendriver.__file__, "python", sys.version.split()[0])

BUSY_JS = "window.__iv = setInterval(() => console.log('tick ' + Date.now()), 30); 1"


async def make_busy_tab(browser):
    tab = await browser.get("about:blank", new_tab=True)
    ticks = []
    tab.add_handler(cdp.runtime.ConsoleAPICalled, lambda ev: ticks.append(1))
    await tab.evaluate(BUSY_JS)
    return tab, ticks


async def run(browser, variant: str) -> None:
    tab, ticks = await make_busy_tab(browser)
    if variant == "await-tab":
        async def _w():
            await tab
        waiter = asyncio.create_task(_w())
    else:
        waiter = asyncio.create_task(tab.wait())
    await asyncio.sleep(0.5)
    print(f"[{variant}] busy: ticks so far={len(ticks)} waiter done={waiter.done()}")
    t0 = asyncio.get_running_loop().time()
    if variant == "control":
        await tab.evaluate("clearInterval(window.__iv); 1")
    elif variant in ("closeTarget", "await-tab"):
        await browser.connection.send(cdp.target.close_target(tab.target_id))
    elif variant == "tab.close":
        await tab.close()
    elif variant == "window.close":
        await tab.evaluate("window.close(); 1")
    done, _ = await asyncio.wait({waiter}, timeout=8)
    dt = asyncio.get_running_loop().time() - t0
    lst = tab.listener
    print(f"[{variant}] waiter done={bool(done)} after {dt:.2f}s; session_id={tab.session_id} "
          f"listener running={lst.running if lst else None}")
    if done:
        exc = waiter.exception()
        print(f"[{variant}] waiter result: exception={exc!r}")
    else:
        print(f"[{variant}] HANG; stack:")
        waiter.print_stack(file=sys.stdout)
        waiter.cancel()
        try:
            await waiter
        except BaseException as e:
            print(f"[{variant}] after cancel: {type(e).__name__}")
    if variant == "control":
        await tab.close()


async def main() -> None:
    browser = await zendriver.start(headless=True)
    try:
        for v in ("control", "closeTarget", "await-tab", "tab.close"):
            await asyncio.wait_for(run(browser, v), 40)
    finally:
        await browser.stop()


asyncio.run(main())
