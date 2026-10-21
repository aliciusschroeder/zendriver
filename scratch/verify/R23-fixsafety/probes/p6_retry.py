import asyncio, sys
import zendriver as zd
print("zendriver from", zd.__file__)
async def main():
    b = await zd.start(headless=True)
    await b.get("about:blank")
    b._process.kill(); b._process.wait()
    for attempt in range(2):
        try:
            await asyncio.wait_for(b.start(), 60)
            print("attempt", attempt, "restart OK; eval", await (await b.get("about:blank")).evaluate("1+1"))
            break
        except Exception as e:
            print("attempt", attempt, "raised", type(e).__name__, "process still set:", b._process is not None)
    await b.stop()
    print("final stopped", b.stopped)
asyncio.run(main())
