"""
Q12 / SEED-X1 via zendriver's own internal timeout: Tab.wait_for_ready_state(timeout=2)
wraps its poll loop in asyncio.wait_for. Page blocked (alert dialog or busy JS), a handler
for a not-yet-enabled domain exists -> the timeout's cancel lands in the nested X.enable.
"""
import asyncio
import sys
import time

import zendriver
from zendriver import cdp

print("python", sys.version.split()[0], "zendriver from", zendriver.__file__)


def coro_chain(task):
    out = []
    c = task.get_coro()
    while c is not None:
        f = getattr(c, "cr_frame", None) or getattr(c, "gi_frame", None)
        if f is None:
            break
        out.append(f"{f.f_code.co_filename.split('/zendriver/')[-1]}:{f.f_lineno} in {f.f_code.co_name}")
        c = getattr(c, "cr_await", None) or getattr(c, "gi_yieldfrom", None)
    return out


BLOCKERS = {
    "alert": "setTimeout(() => alert('blocked'), 100); 1",
    "busy8s": "setTimeout(() => { const e = Date.now() + 8000; while (Date.now() < e) {} }, 100); 1",
}


async def scenario(browser, blocker, with_handler):
    tab = await browser.get("data:text/html,<h1>hi</h1>", new_tab=True)
    await tab.send(cdp.runtime.evaluate(BLOCKERS[blocker]))
    await asyncio.sleep(0.6)
    if with_handler:
        tab.add_handler(cdp.log.EntryAdded, lambda e: None)
    t0 = time.monotonic()
    # 'loading' never matches again, so only the timeout can end the poll
    task = asyncio.create_task(tab.wait_for_ready_state("loading", timeout=2))
    done, _ = await asyncio.wait({task}, timeout=15)
    el = time.monotonic() - t0
    print(f"\n=== blocker={blocker} handler={with_handler}: wait_for_ready_state('loading', timeout=2)")
    if not done:
        print(f"  {el:.2f}s: STILL RUNNING 15s after a 2s timeout (HANG); cancelling()={task.cancelling()}")
        print("  task.print_stack():")
        task.print_stack(file=sys.stdout)
        print("  cr_await chain:")
        for line in coro_chain(task):
            print("     ", line)
        task.cancel()
        d2, _ = await asyncio.wait({task}, timeout=5)
        print(f"  after a 2nd cancel: done={bool(d2)}")
    else:
        exc = None if task.cancelled() else task.exception()
        print(f"  {el:.2f}s: finished with {exc!r}")
    await asyncio.wait_for(tab.close(), 10)


async def main():
    browser = await zendriver.start(headless=True)
    try:
        for blocker in ("alert", "busy8s"):
            await scenario(browser, blocker, False)
            await scenario(browser, blocker, True)
    finally:
        await browser.stop()


asyncio.run(asyncio.wait_for(main(), 140))
