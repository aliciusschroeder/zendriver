import asyncio, logging
import zendriver as zd
from zendriver import cdp

async def main():
    browser = await zd.start(headless=True, browser_connection_max_tries=8)
    print("first start pid", browser._process_pid, "port", browser.config.port)
    await browser.stop()
    print("stopped", browser.stopped, "host/port", browser.config.host, browser.config.port)
    try:
        b2 = await browser.start()
        print("restart returned", b2 is browser, "pid", b2._process_pid, "stopped", b2.stopped)
        t = await asyncio.wait_for(b2.get("about:blank"), 10)
        print("restart works", await t.evaluate("1+1"))
        await b2.stop()
    except Exception as e:
        print("restart raised", type(e).__name__, str(e).strip().splitlines()[:3])
    # externally killed path
    b3 = await zd.start(headless=True, browser_connection_max_tries=8)
    b3._process.kill(); b3._process.wait()
    try:
        b4 = await b3.start()
        print("after external death start returned new", b4 is not b3, "pid", b4._process_pid)
        await b4.stop()
    except Exception as e:
        print("start after external death raised", type(e).__name__, str(e).strip().splitlines()[:3])
    await b3.stop()

asyncio.run(asyncio.wait_for(main(), 50))
