import asyncio, os, signal
import zendriver as zd
from zendriver import cdp
print("zendriver imported from", zd.__file__)

async def main():
    browser = await zd.start(headless=True)
    try:
        tab = await browser.get("about:blank")
        tab.add_handler(cdp.runtime.ConsoleAPICalled, lambda ev: None)
        await tab.evaluate("setInterval(() => console.log('x'), 30); 1")
        await asyncio.sleep(0.3)
        waiter = asyncio.ensure_future(tab.wait())
        await asyncio.sleep(0.5)
        print("waiter done before kill:", waiter.done())
        os.kill(browser._process.pid, signal.SIGKILL)  # the chrome this script started
        done, _ = await asyncio.wait({waiter}, timeout=4)
        if done:
            print("RESULT: tab.wait() finished after the browser died:", repr(waiter.exception()), "| connection.closed =", browser.connection.closed)
        else:
            print("RESULT: tab.wait() still pending 4s after the browser died -> HANG | connection.closed =", browser.connection.closed)
            waiter.cancel()
    finally:
        await browser.stop()

asyncio.run(asyncio.wait_for(main(), 60))
