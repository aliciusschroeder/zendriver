"""Real headless Chromium check for SEED-X1.

1. Chrome behaviour: with a renderer stuck in `while(true){}` / an open alert(),
   which commands does Chrome still answer?
2. End to end: a handler for a not-yet-enabled domain + wait_for(tab.evaluate(), 3)
   on a hung page.
"""
import asyncio
import sys
import time

import zendriver as zd
from zendriver import cdp
from stackwalk import coro_chain

print("zendriver from", zd.__file__, "python", sys.version.split()[0])


async def probe(label, aw, t=3.0):
    t0 = time.monotonic()
    try:
        r = await asyncio.wait_for(aw, t)
        print(f"  {label}: answered in {time.monotonic()-t0:.2f}s -> {str(r)[:60]!r}")
        return True
    except asyncio.TimeoutError:
        print(f"  {label}: NO ANSWER within {t}s")
        return False
    except Exception as e:
        print(f"  {label}: error {type(e).__name__}: {str(e)[:80]}")
        return None


async def e2e(label, tab, coro_factory, inner, net):
    t0 = time.monotonic()
    task = asyncio.create_task(asyncio.wait_for(coro_factory(), inner))
    done, _ = await asyncio.wait({task}, timeout=net)
    dt = time.monotonic() - t0
    if done:
        try:
            r = task.result()
            print(f"  [{label}] returned {r!r} after {dt:.2f}s (no TimeoutError)")
        except BaseException as e:
            print(f"  [{label}] raised {type(e).__name__} after {dt:.2f}s")
        return None
    print(f"  [{label}] HUNG: still running {dt:.1f}s after start, inner timeout was {inner}s")
    print("    chain:", " -> ".join(coro_chain(task)))
    return task


async def main():
    browser = await zd.start(headless=True)
    print("browser pid", browser._process_pid if hasattr(browser, "_process_pid") else browser._process.pid)
    leftover = []
    try:
        tab = await browser.get("data:text/html,<p>hello</p>")
        print("responsive page:")
        await probe("Network.enable (oneshot)", tab._send_oneshot(cdp.network.enable()))
        await tab.send(cdp.network.disable())

        # ---- hung renderer ----
        await tab.evaluate("setTimeout(() => { while (true) {} }, 300); 1")
        await asyncio.sleep(1.0)
        print("hung renderer (while(true)):")
        await probe("Runtime.evaluate", tab._send_oneshot(cdp.runtime.evaluate("1+1")))
        await probe("Page.enable", tab._send_oneshot(cdp.page.enable()))
        await probe("Runtime.enable", tab._send_oneshot(cdp.runtime.enable()))
        await probe("Page.getFrameTree", tab._send_oneshot(cdp.page.get_frame_tree()))
        await probe("Target.getTargetInfo (browser conn)", browser.connection.send(cdp.target.get_target_info(tab.target_id)))

        print("control: no handler, wait_for(tab.evaluate, 3):")
        await e2e("control", tab, lambda: tab.evaluate("2+2"), 3.0, 10.0)

        print("bug: handler for cdp.network (not yet enabled), wait_for(tab.evaluate, 3):")
        tab.add_handler(cdp.network.RequestWillBeSent, lambda e: None)
        t = await e2e("bug-hung-renderer", tab, lambda: tab.evaluate("3+3"), 3.0, 40.0)
        if t:
            leftover.append(t)
            print("    pending tx methods:", sorted(tx.method for tx in tab.mapper.values() if not tx.done()))
            infos = await asyncio.wait_for(browser.connection.send(cdp.target.get_targets()), 5)
            print("    target still listed after 40s:", any(i.target_id == tab.target_id for i in infos))

        # ---- open alert() dialog on a fresh tab ----
        tab2 = await browser.get("data:text/html,<p>dialog</p>", new_tab=True)
        await tab2.evaluate("setTimeout(() => alert('x'), 300); 1")
        await asyncio.sleep(1.0)
        print("open alert() dialog:")
        await probe("Runtime.evaluate", tab2._send_oneshot(cdp.runtime.evaluate("1+1")))
        await probe("Network.enable (oneshot)", tab2._send_oneshot(cdp.network.enable()))
        print("bug: handler for cdp.page (not yet enabled), tab2.wait_for_ready_state(timeout=3):")
        tab2.add_handler(cdp.page.LifecycleEvent, lambda e: None)
        t2 = await e2e("bug-dialog", tab2, lambda: tab2.wait_for_ready_state("complete", timeout=3), 4.0, 20.0)
        if t2:
            leftover.append(t2)
            print("    pending tx methods:", sorted(tx.method for tx in tab2.mapper.values() if not tx.done()))
    finally:
        for t in leftover:
            for _ in range(3):
                t.cancel()
                await asyncio.sleep(0.2)
            print("leftover task done after 3 cancels?", t.done())
        await asyncio.wait_for(browser.stop(), 30)
        for t in leftover:
            await asyncio.wait({t}, timeout=5)
            if t.done():
                try:
                    t.result()
                    print("leftover finished with result after stop")
                except BaseException as e:
                    print("leftover finished after stop with", type(e).__name__, str(e)[:60])
            else:
                print("leftover still pending after stop")


asyncio.run(main())
