import asyncio, logging, sys
import zendriver as zd
from zendriver import cdp
logging.getLogger("uc.connection").setLevel(logging.CRITICAL)
print("python", sys.version.split()[0], "zendriver:", zd.__file__, flush=True)

BROWSER_LEVEL = False
def bad_custom_cmd():
    j = yield ({"method": "Target.getTargets", "params": {}} if BROWSER_LEVEL else {"method": "Runtime.evaluate", "params": {"expression": "1"}})
    return j["notThere"]

async def bounded(label, coro, t=5):
    task = asyncio.ensure_future(coro)
    done, _ = await asyncio.wait({task}, timeout=t)
    if not done:
        print(f"{label}: HUNG (> {t}s)", flush=True)
        task.cancel(); await asyncio.wait({task}, timeout=2)
        return
    exc = task.exception()
    print(f"{label}: {'raised ' + type(exc).__name__ if exc else 'ok -> ' + repr(task.result())[:60]}", flush=True)

async def main():
    browser = await zd.start(headless=True)
    try:
        tab = await browser.get("about:blank")
        print("tab session flat:", tab.session_id is not None, flush=True)
        await bounded("tab.send(bad custom cmd)", tab.send(bad_custom_cmd()))
        await bounded("tab.evaluate after", tab.evaluate("1+1"))
        global BROWSER_LEVEL; BROWSER_LEVEL = True
        await bounded("browser.connection.send(bad custom cmd)", browser.connection.send(bad_custom_cmd()))
        bl = browser.connection.listener
        print("browser listener running:", bl.running, "exc:", (bl.task.exception() if bl.task.done() and not bl.task.cancelled() else None), flush=True)
        await bounded("tab.evaluate after browser-level failure", tab.evaluate("2+2"))
    finally:
        await asyncio.wait_for(browser.stop(), 30)

asyncio.run(main())
