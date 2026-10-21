import asyncio
import sys
import threading
import time

import zendriver as zd
from zendriver.core import util


async def main(n: int) -> None:
    print("zendriver", zd.__file__)
    b = await zd.start(
        headless=True, browser_args=["--enable-logging=stderr", "--v=1"]
    )
    tab = b.main_tab
    hung = False
    i = 0
    for i in range(n):
        try:
            await asyncio.wait_for(
                tab.evaluate("console.log('x'.repeat(2000)); 1+1"), 10
            )
        except asyncio.TimeoutError:
            print("round", i, "TIMEOUT")
            hung = True
            break
    tails = getattr(util, "_stderr_tails", None)
    tail = tails.get(b._process) if tails is not None else None
    print(
        "RESULT hung",
        hung,
        "rounds",
        i + 1,
        "tail len",
        len(tail._data) if tail else None,
    )
    print("threads", [t.name for t in threading.enumerate()])
    t0 = time.monotonic()
    try:
        await asyncio.wait_for(b.stop(), 20)
        print("stop ok in %.1fs" % (time.monotonic() - t0))
    except asyncio.TimeoutError:
        print("stop TIMEOUT")
        if b._process:
            b._process.kill()
    await asyncio.sleep(2)
    print(
        "threads after stop",
        [t.name for t in threading.enumerate()],
        "tracked",
        len(tails) if tails is not None else None,
    )


asyncio.run(main(int(sys.argv[1])))
