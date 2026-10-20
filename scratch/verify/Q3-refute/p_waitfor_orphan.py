import asyncio, os, sys, signal
import zendriver as zd
print("zendriver from", zd.__file__, "python", sys.version.split()[0], file=sys.stderr)
async def main():
    b = await zd.start(headless=True)
    pid = b._process_pid; udd = b.config.user_data_dir
    print(pid, udd)
    await b.get("about:blank")
    os.kill(pid, signal.SIGSTOP)        # browser wedged for a while
    try:
        await asyncio.wait_for(b.stop(), 5)
    except asyncio.TimeoutError:
        print("stop timed out", file=sys.stderr)
    os.kill(pid, signal.SIGCONT)        # browser recovers
    await asyncio.sleep(1)
asyncio.run(main())
