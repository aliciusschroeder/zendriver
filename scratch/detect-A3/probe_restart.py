import asyncio, time, logging
import zendriver as zd

async def main():
    b = await zd.start(headless=True)
    print("first start: host/port", b.config.host, b.config.port, "pid", b._process_pid)
    await b.stop()
    print("after stop: host/port", b.config.host, b.config.port, "info is stale:", bool(b.info), "targets:", len(b.targets))
    t0 = time.monotonic()
    try:
        r = await asyncio.wait_for(b.start(), 30)
        print("restart returned", r, "process", b._process)
    except Exception as e:
        print("restart raised after %.2fs:" % (time.monotonic()-t0), type(e).__name__, e)
    print("process after restart:", b._process, "pid", b._process_pid)

asyncio.run(main())
