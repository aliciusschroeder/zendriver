import asyncio, sys, time, traceback
import zendriver as zd
print("zendriver from", zd.__file__, sys.version.split()[0])

async def main():
    b = await zd.start(headless=True)
    pid1 = b._process_pid
    print("started pid", pid1, "host/port", b.config.host, b.config.port)
    await b.stop()
    print("after stop: host/port", b.config.host, b.config.port, "info stale:", b.info is not None, "targets:", len(b.targets), "process", b._process)
    t = time.monotonic()
    try:
        await asyncio.wait_for(b.start(), 30)
        print("restart OK; pid", b._process_pid, "tabs", len(b.tabs))
        page = await asyncio.wait_for(b.get("about:blank"), 15)
        print("get after restart OK", page)
    except Exception as e:
        print("restart raised after %.2fs: %s %r" % (time.monotonic()-t, type(e).__name__, str(e)[:200]))
    finally:
        print("process after restart attempt", b._process)
        try:
            await asyncio.wait_for(b.stop(), 15)
        except Exception as e:
            print("stop err", e)

    # crash case
    b = await zd.start(headless=True)
    pid1 = b._process_pid
    b._process.kill(); b._process.wait()
    print("killed pid", pid1, "stopped:", b.stopped)
    t = time.monotonic()
    try:
        nb = await asyncio.wait_for(b.start(), 30)
        print("start after crash returned", nb is b, "new pid", nb._process_pid)
        await nb.stop()
    except Exception as e:
        print("start after crash raised after %.2fs: %s %r" % (time.monotonic()-t, type(e).__name__, str(e).split("\n")[:4]))
    finally:
        try:
            await asyncio.wait_for(b.stop(), 15)
        except Exception as e:
            print("stop err", type(e).__name__, e)

asyncio.run(main())
