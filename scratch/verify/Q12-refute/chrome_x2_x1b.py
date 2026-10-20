"""Real headless Chromium:
 X2: Element.mouse_click swallows a cancel landing in flash(); Element.click does not.
 X1b: realistic flow: page with an open alert(), then
      `async with tab.expect_request(...)`: await tab.get(url, timeout=3)
"""
import asyncio
import sys
import time

import zendriver as zd
from zendriver import cdp
from stackwalk import coro_chain

print("zendriver from", zd.__file__, "python", sys.version.split()[0])

PAGE = (
    "data:text/html,<button id=b style='width:200px;height:80px' "
    "onmouseup=\"window.n=(window.n||0)+1; setTimeout(()=>{const t=Date.now();"
    "while(Date.now()-t<BUSY){}},0)\">btn</button>"
)


async def run_click(tab, meth, busy_ms, mode):
    await tab.get(PAGE.replace("BUSY", str(busy_ms)))
    el = await tab.select("#b")
    after = asyncio.Event()

    async def body():
        await getattr(el, meth)()
        after.set()  # runs only if the cancel was swallowed / never came
        return "completed"

    t0 = time.monotonic()
    if mode == "wait_for":
        task = asyncio.create_task(asyncio.wait_for(body(), 1.0))
    else:
        task = asyncio.create_task(body())
        await asyncio.sleep(1.0)
        task.cancel()
    done, _ = await asyncio.wait({task}, timeout=15)
    dt = time.monotonic() - t0
    if not done:
        print(f"  [{meth} busy={busy_ms} {mode}] HUNG {dt:.1f}s:", " -> ".join(coro_chain(task)))
        task.cancel()
        await asyncio.wait({task}, timeout=5)
        return
    try:
        r = task.result()
        print(f"  [{meth} busy={busy_ms} {mode}] returned {r!r} after {dt:.2f}s, code after the call ran={after.is_set()}  <- cancel/timeout swallowed")
    except BaseException as e:
        print(f"  [{meth} busy={busy_ms} {mode}] {type(e).__name__} after {dt:.2f}s, code after the call ran={after.is_set()}")
    # let the busy loop finish
    await asyncio.sleep(busy_ms / 1000 + 0.5)
    print("    clicks registered by page:", await tab.evaluate("window.n"))


async def main():
    browser = await zd.start(headless=True)
    print("browser pid", browser._process_pid)
    leftover = []
    try:
        tab = browser.main_tab
        print("X2 (renderer busy 3s right after mouseup, so flash() is in flight when the cancel lands):")
        for mode in ("wait_for", "cancel"):
            await run_click(tab, "mouse_click", 3000, mode)
        print("X2 control: Element.click (flash not wrapped):")
        await run_click(tab, "click", 3000, "wait_for")
        print("X2 control: mouse_click on a responsive page (busy=0):")
        await run_click(tab, "mouse_click", 0, "wait_for")

        print("X1b: open alert() then expect_request + tab.get(timeout=3)")
        for with_handler in (False, True):
            t = await browser.get("data:text/html,<p>dialog</p>", new_tab=True)
            await t.evaluate("setTimeout(() => alert('x'), 300); 1")
            await asyncio.sleep(1.0)

            async def flow():
                if with_handler:
                    async with t.expect_request("*") as req:
                        await t.get("data:text/html,<p>next</p>", timeout=3)
                        return "navigated"
                await t.get("data:text/html,<p>next</p>", timeout=3)
                return "navigated"

            t0 = time.monotonic()
            task = asyncio.create_task(flow())
            done, _ = await asyncio.wait({task}, timeout=25)
            dt = time.monotonic() - t0
            lab = "expect_request" if with_handler else "control-no-handler"
            if done:
                try:
                    print(f"  [{lab}] returned {task.result()!r} after {dt:.2f}s")
                except BaseException as e:
                    print(f"  [{lab}] {type(e).__name__} after {dt:.2f}s")
            else:
                print(f"  [{lab}] HUNG {dt:.1f}s (tab.get timeout=3):", " -> ".join(coro_chain(task)))
                print("    pending tx:", sorted(x.method for x in t.mapper.values() if not x.done()))
                leftover.append(task)
    finally:
        for task in leftover:
            for _ in range(3):
                task.cancel()
                await asyncio.sleep(0.2)
        await asyncio.wait_for(browser.stop(), 30)
        for task in leftover:
            await asyncio.wait({task}, timeout=5)
            print("leftover done:", task.done())


asyncio.run(main())
