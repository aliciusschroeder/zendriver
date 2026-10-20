import asyncio, os, sys, signal, shutil, time, subprocess
import zendriver as zd
print("zendriver from", zd.__file__, "python", sys.version.split()[0])
async def one(blocking):
    b = await zd.start(headless=True)
    pid = b._process_pid; udd = b.config.user_data_dir
    try:
        tab = await b.get("about:blank"); await tab.evaluate("1")
        subprocess.Popen(["sh", "-c", f"sleep 0.2; kill -9 {pid}"])
        if blocking: time.sleep(1.0)
        else: await asyncio.sleep(1.0)
        out = []
        for attempt in range(2):
            try:
                await asyncio.wait_for(b.stop(), 30); out.append("ok")
            except Exception as e:
                out.append("RAISED %s" % type(e).__name__)
            out.append("profile exists: %s" % os.path.exists(udd))
        return out
    finally:
        try: os.kill(pid, signal.SIGKILL)
        except ProcessLookupError: pass
        if b._process: b._process.wait()
        shutil.rmtree(udd, ignore_errors=True)
async def main():
    print("blocking:", await one(True))
    print("idle loop:", await one(False))
asyncio.run(main())
