import asyncio, os, sys, subprocess, tempfile, time, shutil
import zendriver as zd

CHROME = sys.argv[1]
async def main():
    udd = tempfile.mkdtemp()
    port = zd.util.free_port()
    p = subprocess.Popen([CHROME, "--headless=new", "--no-sandbox", f"--remote-debugging-port={port}", f"--user-data-dir={udd}", "about:blank"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    time.sleep(2)
    os.environ["PATH"] = "/usr/bin:/bin"  # no chromium on PATH now
    try:
        try:
            b = await zd.start(host="127.0.0.1", port=port)
            print("connected without local binary:", b)
            await b.stop()
        except Exception as e:
            print("start(host, port) failed:", type(e).__name__, str(e)[:90])
        b = await zd.start(host="127.0.0.1", port=port, browser_executable_path="/nonexistent")
        print("with dummy executable path:", b.info.Browser if b.info else None)
        await b.stop()
    finally:
        p.kill(); p.wait(); shutil.rmtree(udd, ignore_errors=True)

asyncio.run(asyncio.wait_for(main(), 60))
