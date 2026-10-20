import asyncio, json, subprocess, tempfile, shutil, urllib.request
import zendriver as zd

CHROME = "/tmp/claude-0/-home-user-zendriver/b2021b39-94e6-5220-9e66-7f33c0314a80/scratchpad/bin/chromium"
async def main():
    udd = tempfile.mkdtemp(prefix="a3probe_")
    port = 9557
    p = subprocess.Popen([CHROME, "--headless=new", "--no-sandbox", f"--remote-debugging-port={port}", f"--user-data-dir={udd}", "--remote-allow-origins=*", "about:blank"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        for _ in range(50):
            try:
                urllib.request.urlopen(f"http://127.0.0.1:{port}/json/version"); break
            except Exception: await asyncio.sleep(0.2)
        try:
            b = await zd.start(host="127.0.0.1", port=port)
            print("connected:", b.websocket_url, "stopped property:", b.stopped)
            # second start() on a connected browser
            old = b.connection
            await b.start()
            print("second start(): connection replaced:", b.connection is not old, "old still open:", not old.closed, "old listener running:", old.listener.running if old.listener else None)
            await b.stop()
        except Exception as e:
            print("zd.start(host, port) raised", type(e).__name__, e)
    finally:
        p.kill(); p.wait(); shutil.rmtree(udd, ignore_errors=True)

asyncio.run(main())
