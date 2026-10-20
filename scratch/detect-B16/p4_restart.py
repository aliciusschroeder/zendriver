import asyncio, os
import zendriver as zd

async def main():
    b = await zd.start(headless=True, browser_connection_max_tries=3)
    port = b.config.port
    await b.stop()
    print("stopped; config host/port still", b.config.host, b.config.port, "targets kept:", len(b.targets))
    try:
        r = await asyncio.wait_for(b.start(), 20)
        print("restart returned", r is b, "pid", b._process_pid, "port", b.config.port)
        t = await asyncio.wait_for(b.get("about:blank"), 10)
        print("works", await t.evaluate("1+1"))
    except Exception as e:
        print("restart after stop failed:", type(e).__name__, repr(e)[:200], "process launched?", b._process_pid)
    await b.stop()

    # externally died process
    b = await zd.start(headless=True, browser_connection_max_tries=3)
    b._process.kill(); b._process.wait()
    try:
        nb = await asyncio.wait_for(b.start(), 20)
        print("restart after crash returned new instance?", nb is not b, "new pid", nb._process_pid)
        await nb.stop()
    except Exception as e:
        print("restart after crash failed:", type(e).__name__, repr(e)[:120].replace("\\n"," "))
    await b.stop()

asyncio.run(asyncio.wait_for(main(), 55))
