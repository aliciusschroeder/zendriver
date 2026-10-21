import asyncio, threading, gc
import zendriver as zd
from zendriver.core import util

def drains() -> int:
    return sum(t.name == "zendriver-browser-stderr" for t in threading.enumerate())

async def main() -> None:
    for i in range(3):
        b = await zd.start(headless=True)
        await b.get("about:blank")
        print("running: drain threads", drains())
        await b.stop()
    await asyncio.sleep(2)
    gc.collect()
    print("after stop: drain threads", drains(), "tracked", len(util._stderr_tails))

asyncio.run(main())
