import asyncio, sys, subprocess, tempfile, shutil, os, warnings
import zendriver as zd
from zendriver.core import util
print("zendriver from", zd.__file__, sys.version.split()[0])

async def main():
    port = util.free_port()
    d = tempfile.mkdtemp(prefix="r23ext_", dir="/tmp/claude-0/-home-user-zendriver/b2021b39-94e6-5220-9e66-7f33c0314a80/scratchpad/verify/R23-fixsafety")
    p = subprocess.Popen(["chromium", "--headless=new", "--no-sandbox", f"--remote-debugging-port={port}", f"--user-data-dir={d}", "--remote-allow-origins=*", "about:blank"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        for _ in range(40):
            await asyncio.sleep(0.25)
            try:
                b = await asyncio.wait_for(zd.start(host="127.0.0.1", port=port), 20)
                break
            except Exception as e:
                last = e
        else:
            raise last
        print("connected; stopped:", b.stopped, "tabs:", len(b.tabs), "conn closed:", b.connection.closed)
        old = b.connection
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            r = await asyncio.wait_for(b.start(), 20)
        print("second start warnings:", [str(x.message) for x in w])
        print("connection replaced:", b.connection is not old, "old closed:", old.closed, "old listener running:", bool(old._listener_task and not old._listener_task.done()) if hasattr(old, "_listener_task") else getattr(old, "listener", None))
        await asyncio.sleep(0.5)
        # check whether stop closes old
        print("old.listener", getattr(old, "listener", None) and getattr(old.listener, "running", None))
        # don't close the browser via stop (would send Browser.close)... actually test stop
        await b.stop()
        print("after stop: new closed", b.connection.closed, "old closed", old.closed, "old listener running", getattr(old, "listener", None) and old.listener.running)
        await old.aclose()
    finally:
        p.terminate()
        try: p.wait(5)
        except Exception: p.kill(); p.wait()
        shutil.rmtree(d, ignore_errors=True)

asyncio.run(main())
