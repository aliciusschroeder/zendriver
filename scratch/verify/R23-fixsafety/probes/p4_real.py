import asyncio, sys, subprocess, tempfile, shutil, warnings, time
import zendriver as zd
from zendriver.core import util
print("zendriver from", zd.__file__, sys.version.split()[0])
SD = "/tmp/claude-0/-home-user-zendriver/b2021b39-94e6-5220-9e66-7f33c0314a80/scratchpad/verify/R23-fixsafety"

async def main():
    # 1. crash then immediate start, without yielding to the loop in between
    b = await zd.start(headless=True)
    page = await b.get("about:blank")
    pid = b._process_pid
    b._process.kill(); b._process.wait()
    t = time.monotonic()
    try:
        r = await asyncio.wait_for(b.start(), 60)
        print("immediate restart after kill OK", r is b, b._process_pid != pid, "%.2fs" % (time.monotonic()-t))
        p2 = await b.get("about:blank")
        print("eval", await p2.evaluate("1+2"), "old page object in tabs:", page in b.tabs)
    except Exception as e:
        print("immediate restart raised", type(e).__name__, e)
    finally:
        await b.stop()
    # 2. host/port connected real chrome: tab survives a second start()
    port = util.free_port()
    d = tempfile.mkdtemp(prefix="r23ext_", dir=SD)
    p = subprocess.Popen(["chromium", "--headless=new", "--no-sandbox", f"--remote-debugging-port={port}", f"--user-data-dir={d}", "--remote-allow-origins=*", "about:blank"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        for _ in range(40):
            await asyncio.sleep(0.25)
            try:
                b = await asyncio.wait_for(zd.start(host="127.0.0.1", port=port), 20); break
            except Exception as e:
                last = e
        else:
            raise last
        tab = await b.get("data:text/html,<title>x</title>hello")
        print("connected stopped:", b.stopped, "eval:", await tab.evaluate("document.title"))
        old = b.connection
        await b.start()
        print("second start: old closed", old.closed, "new is old", b.connection is old, "stopped", b.stopped)
        print("old tab still works:", await asyncio.wait_for(tab.evaluate("document.title"), 10), "tabs", len(b.tabs))
        # remote closed by someone else
        await b.connection.send(zd.cdp.browser.close())
        await asyncio.sleep(1)
        print("after remote closed: stopped", b.stopped, "(limitation: closed only flips on aclose)")
        await b.stop()
        print("after stop: stopped", b.stopped, "host/port kept", b.config.host, b.config.port == port)
    finally:
        p.terminate()
        try: p.wait(5)
        except Exception: p.kill(); p.wait()
        shutil.rmtree(d, ignore_errors=True)

asyncio.run(main())
