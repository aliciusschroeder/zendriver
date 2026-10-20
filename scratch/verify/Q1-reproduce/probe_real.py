"""Real headless Chromium: A2.3/B15.1 (custom generator parse failure) + A2.4 (tab hangs after browser listener dies)."""

import asyncio
import io
import sys

import zendriver
from zendriver import cdp

print("zendriver from", zendriver.__file__, "python", sys.version.split()[0])


def stack_tail(task):
    s = io.StringIO()
    task.print_stack(file=s)
    return s.getvalue().strip().splitlines()[-2:]


def bad_custom():
    j = yield {"method": "Browser.getVersion", "params": {}}
    return j["notThere"]


def bad_tab_custom():
    j = yield {"method": "Runtime.evaluate", "params": {"expression": "1"}}
    return j["notThere"]


async def main():
    browser = await zendriver.start(headless=True)
    pending = []
    try:
        tab = browser.main_tab
        print("chrome:", (await browser.connection.send(cdp.browser.get_version()))[1])
        print("tab is flat session:", tab._browser_connection is browser.connection)
        print("tab.evaluate before:", await asyncio.wait_for(tab.evaluate("1+1"), 10))

        # A2.3/B15.1 on the tab's own listener
        old = tab.listener
        t1 = asyncio.create_task(tab.send(bad_tab_custom()))
        pending.append(t1)
        try:
            await asyncio.wait_for(asyncio.shield(t1), 5)
        except asyncio.TimeoutError:
            print("[tab custom gen] hung 5s instead of raising KeyError; tab listener running:", old.running,
                  "exc:", repr(old.task.exception()), "| tab mapper size:", len(tab.mapper))
            print("   stuck at:", stack_tail(t1))
        print("   next tab.evaluate (revives tab listener):", await asyncio.wait_for(tab.evaluate("3+3"), 10),
              "| original done:", t1.done())

        # A2.4: kill the browser connection listener
        bold = browser.connection.listener
        t2 = asyncio.create_task(browser.connection.send(bad_custom()))
        pending.append(t2)
        try:
            await asyncio.wait_for(asyncio.shield(t2), 5)
        except asyncio.TimeoutError:
            print("[browser custom gen] hung 5s; browser listener running:", bold.running,
                  "exc:", repr(bold.task.exception()))
        t3 = asyncio.create_task(tab.evaluate("2+2"))
        pending.append(t3)
        try:
            r = await asyncio.wait_for(asyncio.shield(t3), 8)
            print("[A2.4] tab.evaluate returned", r, "-> NOT reproduced")
        except asyncio.TimeoutError:
            print("[A2.4] tab.evaluate hung 8s | tab listener running:", tab.listener.running,
                  "| tab inbox:", tab._inbox.qsize(), "| browser listener running:", browser.connection.listener.running)
            print("   stuck at:", stack_tail(t3))
        await asyncio.wait_for(browser.connection.send(cdp.target.get_targets()), 10)
        await asyncio.sleep(0.5)
        print("[A2.4] after browser-level send: tab.evaluate done:", t3.done(), "value:", t3.result() if t3.done() else None,
              "| t2 (lost tx) done:", t2.done())
    finally:
        for t in pending:
            if not t.done():
                t.cancel()
                try:
                    await t
                except BaseException:
                    pass
        await browser.stop()
        print("browser stopped")


asyncio.run(asyncio.wait_for(main(), 90))
