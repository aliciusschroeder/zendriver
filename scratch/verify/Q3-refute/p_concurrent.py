import asyncio, os, sys, signal, shutil, time
import zendriver as zd
print("zendriver from", zd.__file__, "python", sys.version.split()[0])
MODE = sys.argv[1]
async def one():
    b = await zd.start(headless=True)
    pid = b._process_pid; udd = b.config.user_data_dir
    try:
        if MODE != "fresh":
            await b.get("about:blank")
        res = await asyncio.wait_for(asyncio.gather(b.stop(), b.stop(), return_exceptions=True), 30)
        return [repr(r) for r in res], "profile exists: %s" % os.path.exists(udd)
    finally:
        try: os.kill(pid, signal.SIGKILL)
        except ProcessLookupError: pass
        if b._process: b._process.wait()
        shutil.rmtree(udd, ignore_errors=True)
async def main():
    for i in range(int(sys.argv[2])):
        print(MODE, i, await one())
asyncio.run(main())
