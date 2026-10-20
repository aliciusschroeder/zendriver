"""
Q12 / SEED-X1 on real headless Chromium: a renderer busy in a JS loop never answers
Network.enable; asyncio.wait_for(tab.send(...), 3) should raise TimeoutError after 3s.
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


async def busy_loop(tab, seconds):
    # renderer main thread busy for `seconds` (bounded so cleanup always works)
    await tab.send(
        cdp.runtime.evaluate(
            f"setTimeout(() => {{ const e = Date.now() + {int(seconds * 1000)}; while (Date.now() < e) {{}} }}, 200); 1"
        )
    )
    await asyncio.sleep(0.6)


async def attempt(tab, label, with_handler, ev=cdp.network.RequestWillBeSent):
    await busy_loop(tab, 12)
    if with_handler:
        tab.add_handler(ev, lambda e: None)  # added AFTER the renderer got busy
    t0 = time.monotonic()
    task = asyncio.create_task(
        asyncio.wait_for(tab.send(cdp.runtime.evaluate("6*7")), 3)
    )
    done, _ = await asyncio.wait({task}, timeout=8)
    el = time.monotonic() - t0
    print(f"\n=== {label} (handler={with_handler}, {ev.__module__}.{ev.__name__})")
    if not done:
        print(f"  {el:.2f}s: STILL RUNNING 8s after wait_for(..., 3) started (timeout ignored)")
        print("  task.cancelling() =", task.cancelling())
        for line in coro_chain(task):
            print("     ", line)
        try:
            res = await asyncio.wait_for(task, 15)
            print(f"  later returned normally after {time.monotonic() - t0:.2f}s: {res}")
        except BaseException as e:
            print(f"  later: {type(e).__name__} after {time.monotonic() - t0:.2f}s")
    elif task.cancelled():
        print(f"  {el:.2f}s: cancelled")
    elif task.exception() is not None:
        print(f"  {el:.2f}s: raised {type(task.exception()).__name__} (correct)")
    else:
        print(f"  {el:.2f}s: returned normally {task.result()} (timeout ignored)")
    print("  enabled_domains:", [m.__name__ for m in tab.enabled_domains])
    tab.remove_handlers()
    await asyncio.sleep(13 - min(el, 13))  # let the busy loop finish


async def main():
    browser = await zendriver.start(headless=True)
    try:
        for label, wh, ev in [
            ("CONTROL no handler", False, cdp.network.RequestWillBeSent),
            ("new Network handler", True, cdp.network.RequestWillBeSent),
            ("new Runtime handler", True, cdp.runtime.ConsoleAPICalled),
            ("new Log handler", True, cdp.log.EntryAdded),
        ]:
            tab = await browser.get("data:text/html,<h1>hi</h1>", new_tab=True)
            await attempt(tab, label, wh, ev)
            await tab.close()
    finally:
        await browser.stop()


asyncio.run(asyncio.wait_for(main(), 160))
