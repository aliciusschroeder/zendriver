"""Real headless Chromium, SEED-X2: Element.mouse_click wraps flash() in a bare except.
The page makes flash()'s own script slow (insertAdjacentElement busy-waits 3s), so the
wait_for timeout / task.cancel() lands inside flash() deterministically, with the real
flash() code (nothing in zendriver is patched)."""
import asyncio
import sys
import time

import zendriver as zd
from stackwalk import coro_chain

print("zendriver from", zd.__file__, "python", sys.version.split()[0])

PAGE = (
    "data:text/html,<button id=b style='width:200px;height:80px' "
    "onmouseup='window.n=(window.n||0)+1' onclick='window.c=(window.c||0)+1'>btn</button>"
    "<script>const orig=HTMLElement.prototype.insertAdjacentElement;"
    "document.body.insertAdjacentElement=function(...a){const t=Date.now();"
    "while(Date.now()-t<BUSY){} return orig.apply(this,a)}</script>"
)


async def run(tab, meth, busy_ms, mode):
    await tab.get(PAGE.replace("BUSY", str(busy_ms)))
    el = await tab.select("#b")
    after = asyncio.Event()

    async def body():
        await getattr(el, meth)()
        after.set()  # only runs if the call returned normally
        return "completed"

    t0 = time.monotonic()
    if mode == "wait_for":
        task = asyncio.create_task(asyncio.wait_for(body(), 1.0))
    else:
        task = asyncio.create_task(body())
        await asyncio.sleep(1.0)
        print("    at cancel time:", " -> ".join(coro_chain(task)[-3:]))
        task.cancel()
    done, _ = await asyncio.wait({task}, timeout=15)
    dt = time.monotonic() - t0
    lab = f"{meth} busy={busy_ms} {mode}"
    if not done:
        print(f"  [{lab}] HUNG {dt:.1f}s")
        task.cancel()
        await asyncio.wait({task}, timeout=5)
        return
    try:
        r = task.result()
        print(f"  [{lab}] returned {r!r} after {dt:.2f}s; code after the call ran={after.is_set()}")
    except BaseException as e:
        print(f"  [{lab}] {type(e).__name__} after {dt:.2f}s; code after the call ran={after.is_set()}")
    await asyncio.sleep(busy_ms / 1000 + 0.5)
    print("    page saw mouseup:", await tab.evaluate("window.n||0"), "click:", await tab.evaluate("window.c||0"))


async def main():
    browser = await zd.start(headless=True)
    print("browser pid", browser._process_pid)
    try:
        tab = browser.main_tab
        for mode in ("wait_for", "cancel"):
            await run(tab, "mouse_click", 3000, mode)
        print("control: Element.click (flash(0.25) not wrapped)")
        await run(tab, "click", 3000, "wait_for")
        print("control: mouse_click, flash fast")
        await run(tab, "mouse_click", 0, "wait_for")
    finally:
        await asyncio.wait_for(browser.stop(), 30)


asyncio.run(main())
