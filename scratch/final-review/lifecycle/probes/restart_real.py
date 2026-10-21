import asyncio, logging, os, shutil, sys, time, glob, tempfile, threading
import zendriver as zd
from zendriver.core import util
logging.basicConfig(level=logging.WARNING, format="LOG %(levelname)s %(name)s: %(message)s")
CHROME = shutil.which("chromium")
async def main():
    print("python", sys.version.split()[0], zd.__file__)
    b = await zd.start(headless=True, sandbox=False, browser_executable_path=CHROME, browser_connection_max_tries=4)
    prof = b.config.user_data_dir
    await b.stop()
    print("after stop: process", b._process, "profile exists", os.path.exists(prof), "registry", len(util.get_registered_instances()))
    t0 = time.monotonic()
    try:
        r = await asyncio.wait_for(b.start(), 30)
        print("restart returned", r is b, "process", b._process and b._process.pid, "connected", b.connection and not b.connection.closed)
        await r.stop()
    except BaseException as e:
        print("restart raised %s: %s after %.2fs" % (type(e).__name__, str(e).strip().splitlines()[1:3] if str(e) else '', time.monotonic() - t0))
    print("registry", len(util.get_registered_instances()), "threads", [t.name for t in threading.enumerate()])
asyncio.run(main())
