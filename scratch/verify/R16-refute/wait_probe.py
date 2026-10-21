"""Real headless Chromium probes for B14.5: Connection.wait() after the tab's session goes away."""

import asyncio
import sys
import time

import zendriver
from zendriver import cdp

print("zendriver from", zendriver.__file__, "python", sys.version.split()[0])

BUSY = "data:text/html,<title>busy</title><script>let i=setInterval(()=>console.log('x'),40);</script>"
BUSY_STOPS = "data:text/html,<title>busy</title><script>let i=setInterval(()=>console.log('x'),40);setTimeout(()=>clearInterval(i),1000)</script>"
QUIET = "data:text/html,<title>quiet</title><p>hi</p>"


async def check(waiter: asyncio.Task, label: str, t0: float, budget: float = 8.0) -> None:
    deadline = time.monotonic() + budget
    while time.monotonic() < deadline and not waiter.done():
        await asyncio.sleep(0.1)
    if waiter.done():
        exc = waiter.exception()
        print(f"[{label}] waiter finished after {time.monotonic()-t0:.2f}s, exc={exc!r}")
    else:
        print(f"[{label}] waiter STILL PENDING after {time.monotonic()-t0:.2f}s -> HANG")
        waiter.print_stack(limit=3)
        waiter.cancel()
        try:
            await waiter
        except BaseException:
            pass


async def new_tab(browser, url):
    tab = await browser.get(url, new_tab=True)
    tab.add_handler(cdp.runtime.ConsoleAPICalled, lambda e: None)
    await tab.send(cdp.runtime.enable())
    return tab


async def main() -> None:
    browser = await zendriver.start(headless=True)
    try:
        # control: busy page that stops being busy after 1s, no close
        tab = await new_tab(browser, BUSY_STOPS)
        await tab.reload()
        t0 = time.monotonic()
        w = asyncio.create_task(tab.wait())
        await check(w, "control busy->idle, no close", t0)

        # A: busy page, tab closed via Target.closeTarget on the browser connection
        tab = await new_tab(browser, BUSY)
        t0 = time.monotonic()
        w = asyncio.create_task(tab.wait())
        await asyncio.sleep(0.3)
        await browser.connection.send(cdp.target.close_target(tab.target_id))
        await check(w, "A busy + Target.closeTarget", t0)
        print("   listener running:", tab.listener.running, "session_id:", tab.session_id)

        # B: busy page, tab.close() from another task
        tab = await new_tab(browser, BUSY)
        t0 = time.monotonic()
        w = asyncio.create_task(tab.wait())
        await asyncio.sleep(0.3)
        await tab.close()
        await check(w, "B busy + tab.close()", t0)

        # C: quiet page that closes itself 50ms later, then `await tab`
        tab = await browser.get(QUIET, new_tab=True)
        await tab.evaluate("1")
        await tab.wait(0.5)
        await tab.evaluate("setTimeout(() => window.close(), 50); 1")
        t0 = time.monotonic()
        w = asyncio.create_task(tab.wait())  # same as `await tab`
        await check(w, "C quiet page, window.close() 50ms later", t0)

        # C2: same with 300ms (outside the idle window) -> should return
        tab = await browser.get(QUIET, new_tab=True)
        await tab.evaluate("1")
        await tab.evaluate("setTimeout(() => window.close(), 300); 1")
        t0 = time.monotonic()
        w = asyncio.create_task(tab.wait())
        await check(w, "C2 quiet page, window.close() 300ms later", t0)
        await asyncio.sleep(0.5)
        print("   C2 tab session_id after close:", tab.session_id)
    finally:
        await browser.stop()


async def main_stop() -> None:
    # D: busy page while browser.stop() runs in another task
    browser = await zendriver.start(headless=True)
    tab = await new_tab(browser, BUSY)
    t0 = time.monotonic()
    w = asyncio.create_task(tab.wait())
    await asyncio.sleep(0.3)
    await browser.stop()
    await check(w, "D busy + browser.stop()", t0)


async def main_kill() -> None:
    # E: busy page, browser process killed (crash)
    browser = await zendriver.start(headless=True)
    tab = await new_tab(browser, BUSY)
    t0 = time.monotonic()
    w = asyncio.create_task(tab.wait())
    await asyncio.sleep(0.3)
    browser._process.kill()
    await check(w, "E busy + browser process killed", t0)
    await browser.stop()


asyncio.run(main())
asyncio.run(main_stop())
asyncio.run(main_kill())
