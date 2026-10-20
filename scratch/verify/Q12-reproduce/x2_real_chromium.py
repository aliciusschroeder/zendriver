"""
Q12 / SEED-X2: `try: await self.flash() except: pass` in Element.mouse_click
swallows CancelledError. Real headless Chromium.
"""
import asyncio
import sys
import time

import zendriver
from zendriver import cdp

print("python", sys.version.split()[0], "zendriver from", zendriver.__file__)

PAGE = "data:text/html,<button id=b onclick='window.n=(window.n||0)+1'>click me</button>"


def coro_chain(task):
    out = []
    c = task.get_coro()
    while c is not None:
        f = getattr(c, "cr_frame", None) or getattr(c, "gi_frame", None)
        if f is None:
            break
        out.append((f.f_code.co_name, f"{f.f_code.co_filename.split('/zendriver/')[-1]}:{f.f_lineno} in {f.f_code.co_name}"))
        c = getattr(c, "cr_await", None) or getattr(c, "gi_yieldfrom", None)
    return out


async def cancel_inside_flash(make_coro, label):
    """start the coroutine, wait until its await chain is inside Element.flash, then cancel it"""
    task = asyncio.create_task(make_coro())
    t0 = time.monotonic()
    chain = []
    while not task.done() and time.monotonic() - t0 < 10:
        chain = coro_chain(task)
        if any(name == "flash" for name, _ in chain):
            break
        await asyncio.sleep(0)
    print(f"\n=== {label}")
    print("  cancelling while suspended at:")
    for _, line in chain:
        print("     ", line)
    task.cancel()
    done, _ = await asyncio.wait({task}, timeout=5)
    if not done:
        print("  STILL RUNNING 5s after cancel")
        task.cancel()
        await asyncio.wait({task}, timeout=5)
    elif task.cancelled():
        print("  RESULT: task.cancelled() == True (CancelledError propagated) -- correct")
    elif task.exception():
        print(f"  RESULT: raised {task.exception()!r}")
    else:
        print(f"  RESULT: returned normally ({task.result()!r}); task.cancelled()={task.cancelled()} "
              f"cancelling()={task.cancelling()} -- CANCEL SWALLOWED")


async def loop_under_timeout(el, label, method, limit=1.5):
    """a caller's timeout around a click loop: should stop after 1.5s"""
    n = 0

    async def body():
        nonlocal n
        async with asyncio.timeout(limit):
            while True:
                await getattr(el, method)()
                n += 1

    t0 = time.monotonic()
    task = asyncio.create_task(body())
    done, _ = await asyncio.wait({task}, timeout=limit + 4)
    el_t = time.monotonic() - t0
    print(f"\n=== {label}: async with asyncio.timeout(limit): while True: await el.{method}()")
    if not done:
        print(f"  {el_t:.2f}s: STILL RUNNING ({n} clicks) -- asyncio.timeout(1.5) never fired (HANG)")
        print("  task.cancelling() =", task.cancelling())
        print("  task.print_stack():")
        task.print_stack(file=sys.stdout)
        task.cancel()
        await asyncio.wait({task}, timeout=5)
        print(f"  after 2nd cancel: done={task.done()} ({n} clicks total)")
        if not task.done():
            task.cancel()
            await asyncio.wait({task}, timeout=5)
            print(f"  after 3rd cancel: done={task.done()}")
    else:
        exc = None if task.cancelled() else task.exception()
        print(f"  {el_t:.2f}s: finished with {exc!r} after {n} clicks")


async def main():
    browser = await zendriver.start(headless=True)
    try:
        tab = await browser.get(PAGE)
        el = await tab.select("#b")
        # control: Element.click() calls flash() without a bare except
        await cancel_inside_flash(lambda: el.click(), "CONTROL Element.click() cancelled inside flash")
        await cancel_inside_flash(lambda: el.mouse_click(), "BUG Element.mouse_click() cancelled inside flash")
        await loop_under_timeout(el, "CONTROL", "click")
        import random
        random.seed(1)
        for i in range(int(sys.argv[1]) if len(sys.argv) > 1 else 3):
            await loop_under_timeout(el, f"BUG run {i}", "mouse_click", round(random.uniform(0.2, 0.6), 3))
        print("\nclick counter in page:", await tab.evaluate("window.n"))
    finally:
        await browser.stop()


asyncio.run(asyncio.wait_for(main(), 110))
