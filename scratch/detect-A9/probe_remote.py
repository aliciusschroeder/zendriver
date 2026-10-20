import asyncio, os, subprocess, tempfile, time, shutil
import zendriver as zd
from zendriver.core import util

async def main():
    chrome = shutil.which("chromium")
    port = util.free_port()
    udd = tempfile.mkdtemp()
    proc = subprocess.Popen([chrome, "--headless=new", "--no-sandbox", f"--remote-debugging-port={port}", f"--user-data-dir={udd}", "about:blank"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    await asyncio.sleep(2)
    os.environ["PATH"] = "/usr/bin:/bin"  # a client machine without a local chrome
    try:
        b = await asyncio.wait_for(zd.start(host="127.0.0.1", port=port), 20)
        print("start(host, port) connected:", b.info.Browser if b.info else None)
    except Exception as e:
        print("start(host, port) raised:", type(e).__name__, " ".join(str(e).split())[:90])
    b = await asyncio.wait_for(zd.start(host="127.0.0.1", port=port, browser_executable_path="/does/not/exist"), 20)
    print("with a bogus browser_executable_path it connects fine:", b.info.Browser)
    await b.connection.aclose()
    proc.kill(); proc.wait()
    shutil.rmtree(udd, ignore_errors=True)
asyncio.run(main())
