"""attach to an external chromium; cancel zd.start(host, port) at increasing delays.
check: external browser still alive, its page target still there, registry empty,
no atexit callbacks registered, no temp profile left."""
import asyncio, glob, json, logging, os, shutil, subprocess, sys, tempfile, time, urllib.request
import asyncio_atexit, psutil
import zendriver as zd
from zendriver.core import util

logging.basicConfig(level=logging.WARNING, format="LOG %(levelname)s %(name)s: %(message)s")
CHROME = shutil.which("chromium")
port = util.free_port()
prof = tempfile.mkdtemp(prefix="ext_")
ext = subprocess.Popen([CHROME, "--headless=new", "--no-sandbox", f"--remote-debugging-port={port}",
                        f"--user-data-dir={prof}", "about:blank"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

def targets():
    with urllib.request.urlopen(f"http://127.0.0.1:{port}/json/list", timeout=2) as r:
        return [t["type"] for t in json.load(r)]

async def main():
    print("python", sys.version.split()[0], zd.__file__)
    for _ in range(100):
        try:
            targets(); break
        except Exception:
            await asyncio.sleep(0.1)
    print("external targets:", targets())
    d = 0.0
    while d <= 0.6:
        before = set(glob.glob(tempfile.gettempdir() + "/uc_*"))
        t0 = time.monotonic()
        try:
            b = await asyncio.wait_for(zd.start(host="127.0.0.1", port=port, headless=True), d)
            outcome = "returned"
        except BaseException as e:
            outcome = type(e).__name__; b = None
        dt = time.monotonic() - t0
        if b is not None:
            # detach without Browser.close
            await b.connection.aclose(); util.get_registered_instances().discard(b); asyncio_atexit.unregister(b._atexit_cleanup)
            await b._cleanup_temporary_profile()
        await asyncio.sleep(0.2)
        left = set(glob.glob(tempfile.gettempdir() + "/uc_*")) - before
        entry = asyncio_atexit._registry.get(asyncio.get_running_loop())
        print(f"d={d:.2f} {outcome:<14} {dt:.2f}s ext_alive={ext.poll() is None} targets={targets()} registry={len(util.get_registered_instances())} atexit={len(entry.callbacks) if entry else 0} profiles_left={len(left)}")
        d += 0.02 if d < 0.2 else 0.1

try:
    asyncio.run(main())
finally:
    ext.terminate(); ext.wait(10); shutil.rmtree(prof, ignore_errors=True)
