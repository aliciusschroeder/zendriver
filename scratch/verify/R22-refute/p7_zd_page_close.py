"""A1.5 via the command that itself ends the session: tab.send(cdp.page.close()) on the tab's
own session. Real headless Chromium. Run idle, then with a CPU-busy sibling task."""
import asyncio, json, time, sys, collections
import zendriver
from zendriver import cdp
from zendriver.core.connection import ProtocolException
print("zendriver from", zendriver.__file__, "py", sys.version.split()[0])
N = int(sys.argv[1]) if len(sys.argv) > 1 else 20
BUSY_MS = float(sys.argv[2]) if len(sys.argv) > 2 else 0.0

async def busy(stop):
    while not stop.is_set():
        t0 = time.perf_counter()
        while time.perf_counter() - t0 < BUSY_MS / 1000: pass
        await asyncio.sleep(0)

async def main():
    browser = await zendriver.start(headless=True)
    out = collections.Counter()
    stop = asyncio.Event()
    try:
        bt = asyncio.create_task(busy(stop)) if BUSY_MS else None
        for i in range(N):
            tab = await browser.get("about:blank", new_tab=True)
            await tab.evaluate("1")
            try:
                await asyncio.wait_for(tab.send(cdp.page.close()), 10)
                out["ok"] += 1
            except ProtocolException as e:
                out["ProtocolException: " + str(e).splitlines()[0]] += 1
            except asyncio.TimeoutError:
                out["TIMEOUT"] += 1
            await asyncio.sleep(0.05)
        stop.set()
        if bt: await bt
        print(f"busy={BUSY_MS}ms outcomes:", dict(out))
    finally:
        await browser.stop()

asyncio.run(main())
