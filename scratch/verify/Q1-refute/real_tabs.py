"""Real headless Chromium: kill the BROWSER connection listener by a realistic route
(user async handler with wrong arity on a target event), then check tab commands."""
import asyncio, sys
import zendriver
from zendriver import cdp
print("zendriver from", zendriver.__file__, "python", sys.version.split()[0])

async def step(label, coro, t=5):
    task = asyncio.ensure_future(coro)
    done, _ = await asyncio.wait({task}, timeout=t)
    if not done:
        print(f"{label}: HUNG ({t}s)")
        task.print_stack(limit=2, file=sys.stdout); sys.stdout.flush()
        task.cancel(); await asyncio.gather(task, return_exceptions=True)
        return None
    exc = task.exception()
    print(f"{label}: {'raised ' + type(exc).__name__ + ': ' + str(exc)[:80] if exc else 'ok -> ' + repr(task.result())[:60]}")
    return task

async def main():
    browser = await zendriver.start(headless=True)
    try:
        tab = browser.main_tab
        await step("warmup tab.evaluate", tab.evaluate("1+1"))
        async def bad():  # wrong arity: user forgot the event parameter
            pass
        browser.connection.add_handler(cdp.target.TargetInfoChanged, bad)
        bl = browser.connection.listener
        await step("tab.send(navigate) after bad handler registered", tab.send(cdp.page.navigate("data:text/html,<title>hello</title>hi")), 8)
        await asyncio.sleep(0.5)
        print("browser listener running:", bl.running, "exc:", repr(bl.task.exception() if bl.task.done() else None)[:100])
        print("tab listener running:", tab.listener.running, "tab inbox size:", tab._inbox.qsize() if tab._inbox else None)
        browser.connection.remove_handlers(cdp.target.TargetInfoChanged, bad)
        await step("A2.4: tab.evaluate after browser listener died", tab.evaluate("2+2"))
        await step("A2.4: tab.send(runtime.evaluate)", tab.send(cdp.runtime.evaluate("3+3")))
        print("browser listener running:", browser.connection.listener.running)
        await step("browser-level send (revives browser listener)", browser.connection.send(cdp.target.get_targets()))
        await step("tab.evaluate after browser-level send", tab.evaluate("4+4"))
    finally:
        await asyncio.wait_for(browser.stop(), 20)

asyncio.run(asyncio.wait_for(main(), 100))
