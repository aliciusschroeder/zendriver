import asyncio, os, sys, signal, shutil, time
import zendriver as zd
print("zendriver from", zd.__file__, "python", sys.version.split()[0])
DELAY = sys.argv[1]  # "none", "yield", or seconds
async def one():
    b = await zd.start(headless=True)
    pid = b._process_pid; udd = b.config.user_data_dir
    res = None
    try:
        tab = await b.get("about:blank")
        await tab.evaluate("1")
        b._process.kill()
        if DELAY == "yield":
            await asyncio.sleep(0)
        elif DELAY != "none":
            await asyncio.sleep(float(DELAY))
        try:
            await asyncio.wait_for(b.stop(), 30)
            res = "ok"
        except Exception as e:
            res = "RAISED %s: %s" % (type(e).__name__, e)
        res += " | _process still set: %s | profile exists: %s" % (b._process is not None, os.path.exists(udd))
    finally:
        try: os.kill(pid, signal.SIGKILL)
        except ProcessLookupError: pass
        if b._process: b._process.wait()
        shutil.rmtree(udd, ignore_errors=True)
    return res
async def main():
    for i in range(int(sys.argv[2])):
        print(DELAY, i, await one())
asyncio.run(main())
