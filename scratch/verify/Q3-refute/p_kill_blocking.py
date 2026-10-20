import asyncio, os, sys, signal, shutil, time, subprocess
import zendriver as zd
print("zendriver from", zd.__file__, "python", sys.version.split()[0])
# Chrome dies (killed from OUTSIDE the event loop, like the OOM killer) while user code does
# 1s of synchronous work without yielding; then the user calls stop().
async def one():
    b = await zd.start(headless=True)
    pid = b._process_pid; udd = b.config.user_data_dir
    try:
        tab = await b.get("about:blank")
        await tab.evaluate("1")
        subprocess.Popen(["sh", "-c", f"sleep 0.2; kill -9 {pid}"])
        time.sleep(1.0)   # blocking work, e.g. parsing HTML
        try:
            await asyncio.wait_for(b.stop(), 30); res = "ok"
        except Exception as e:
            res = "RAISED %s: %s" % (type(e).__name__, e)
        return res + " | _process set: %s | profile exists: %s" % (b._process is not None, os.path.exists(udd))
    finally:
        try: os.kill(pid, signal.SIGKILL)
        except ProcessLookupError: pass
        if b._process: b._process.wait()
        shutil.rmtree(udd, ignore_errors=True)
async def main():
    for i in range(3):
        print(i, await one())
asyncio.run(main())
