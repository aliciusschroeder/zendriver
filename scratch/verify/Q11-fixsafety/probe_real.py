import asyncio, sys, time, pathlib
import zendriver as zd

async def main():
    print("zendriver:", zd.__file__, "python", sys.version.split()[0])
    url = pathlib.Path(sys.argv[1]).as_uri()
    browser = await zd.start(headless=True)
    try:
        tab = await browser.get(url)
        print("readyState right after get:", await tab.evaluate("document.readyState"))
        await asyncio.sleep(0.5)
        print("readyState after 0.5s:", await tab.evaluate("document.readyState"))
        for until in ("interactive", "loading", "complete", None):
            t = time.monotonic()
            try:
                coro = tab.wait_for_ready_state(timeout=2) if until is None else tab.wait_for_ready_state(until, timeout=2)
                r = await asyncio.wait_for(coro, 10)
                print(f"until={until or 'default'}: returned {r} in {time.monotonic()-t:.2f}s")
            except asyncio.TimeoutError as e:
                print(f"until={until or 'default'}: TimeoutError({e}) after {time.monotonic()-t:.2f}s")
    finally:
        await browser.stop()

asyncio.run(main())
