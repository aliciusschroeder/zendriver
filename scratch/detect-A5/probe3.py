import asyncio
import sys
import time

sys.path.insert(0, "/tmp/claude-0/-home-user-zendriver/b2021b39-94e6-5220-9e66-7f33c0314a80/scratchpad/detect-A5")
from server import start_server  # noqa

import zendriver as zd


async def step(name, coro, t=15):
    t0 = time.monotonic()
    task = asyncio.ensure_future(coro)
    try:
        r = await asyncio.wait_for(asyncio.shield(task), t)
        print(f"[{name}] -> {r} after {time.monotonic()-t0:.1f}s")
        return r
    except asyncio.TimeoutError:
        print(f"[{name}] STILL RUNNING after {time.monotonic()-t0:.1f}s (outer safety net). stack:")
        task.print_stack(limit=3)
        task.cancel()
        try:
            await task
        except BaseException:
            pass
    except BaseException as e:
        print(f"[{name}] EXC {type(e).__name__}: {e!s:.200} after {time.monotonic()-t0:.1f}s")


async def main():
    server, base = start_server()
    browser = await zd.start(headless=True)
    try:
        tab = await browser.get(base + "/table")
        await tab.select("tr")
        mode = sys.argv[1] if len(sys.argv) > 1 else "busy"
        if mode == "alert":
            await tab.evaluate("setTimeout(() => alert('blocking'), 100)", await_promise=False)
        else:
            await tab.evaluate("setTimeout(() => { const e = Date.now() + 60000; while (Date.now() < e) {} }, 100)", await_promise=False)
        await asyncio.sleep(0.5)
        await step("select missing timeout=2", tab.select("#missing", timeout=2))
        await step("find missing timeout=2", tab.find("no such text", timeout=2))
        await step("xpath timeout=1", tab.xpath("//nothing", timeout=1))
    finally:
        await browser.stop()
        server.shutdown()


asyncio.run(main())
