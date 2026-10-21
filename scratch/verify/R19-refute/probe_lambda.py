"""Real-Chromium probe: which handler shapes actually run their async work."""
import asyncio
import functools
import gc
import sys
import threading
import warnings

import zendriver
from zendriver import cdp

print("zendriver from", zendriver.__file__, "python", sys.version.split()[0])
warnings.simplefilter("always")


async def main() -> None:
    loop = asyncio.get_running_loop()
    loop_errors: list[str] = []
    loop.set_exception_handler(
        lambda lp, ctx: loop_errors.append(f"{ctx.get('message')} | {ctx.get('exception')!r}")
    )
    ran: dict[str, int] = {}

    async def process(tag: str, e) -> None:
        ran[tag] = ran.get(tag, 0) + 1

    class AsyncCallable:
        async def __call__(self, e) -> None:
            ran["async_call_obj"] = ran.get("async_call_obj", 0) + 1

    sync_ran: list[str] = []

    browser = await zendriver.start(headless=True)
    try:
        tab = await browser.get("about:blank")
        await tab.send(cdp.runtime.enable())
        E = cdp.runtime.ConsoleAPICalled
        tab.add_handler(E, lambda e: process("lambda_returns_coro", e))
        tab.add_handler(E, lambda e: asyncio.create_task(process("lambda_create_task", e)))
        tab.add_handler(E, AsyncCallable())
        tab.add_handler(E, functools.partial(process, "partial_async"))
        tab.add_handler(E, lambda e: sync_ran.append(threading.current_thread().name))
        tab.add_handler(E, lambda event: print("documented lambda example ran in", threading.current_thread().name))
        await tab.send(cdp.runtime.evaluate("console.log('hi')"))
        await asyncio.sleep(1.5)
        gc.collect()
        await asyncio.sleep(0.2)
        print("async work that ran:", ran)
        print("plain sync lambda ran in threads:", sync_ran)
        print("loop errors:", loop_errors)
    finally:
        await browser.stop()


asyncio.run(main())
