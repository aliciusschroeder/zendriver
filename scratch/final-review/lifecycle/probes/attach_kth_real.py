"""attach to an external chromium; cancel zd.start(host, port) when it sends its k-th
cdp message (or raise there). check the external browser survives, nothing was sent
after the cancellation that closes it, registry/atexit/profile clean."""
import asyncio, glob, json, logging, os, shutil, subprocess, sys, tempfile, time, urllib.request
import asyncio_atexit, websockets
import zendriver as zd
from zendriver.core import util

logging.basicConfig(level=logging.ERROR, format="LOG %(levelname)s %(name)s: %(message)s")
CHROME = shutil.which("chromium")
MODE = sys.argv[1] if len(sys.argv) > 1 else "cancel"
HEADLESS = (sys.argv[2] == "headless") if len(sys.argv) > 2 else True
port = util.free_port()
prof = tempfile.mkdtemp(prefix="ext_")
ext = subprocess.Popen([CHROME, "--headless=new", "--no-sandbox", f"--remote-debugging-port={port}",
                        f"--user-data-dir={prof}", "about:blank"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

def targets():
    with urllib.request.urlopen(f"http://127.0.0.1:{port}/json/list", timeout=2) as r:
        return [t["type"] for t in json.load(r)]

real_connect = websockets.connect
state = {"k": 0, "n": 0, "task": None, "sent": [], "fired": False}

class WS:
    def __init__(self, ws): self._ws = ws
    def __getattr__(self, a): return getattr(self._ws, a)
    async def send(self, msg):
        m = json.loads(msg)["method"]
        state["n"] += 1
        state["sent"].append(("AFTER " if state["fired"] else "") + m)
        if state["n"] == state["k"] and not state["fired"]:
            state["fired"] = True
            if MODE == "cancel":
                state["task"].cancel()
            else:
                raise RuntimeError("injected send failure")
        return await self._ws.send(msg)

async def connect(*a, **k):
    return WS(await real_connect(*a, **k))
websockets.connect = connect

async def main():
    print("python", sys.version.split()[0], zd.__file__, "mode", MODE, "headless", HEADLESS)
    for _ in range(100):
        try:
            targets(); break
        except Exception:
            await asyncio.sleep(0.1)
    k = 1
    while True:
        state.update(k=k, n=0, sent=[], fired=False)
        before = set(glob.glob(tempfile.gettempdir() + "/uc_*"))
        task = asyncio.ensure_future(zd.start(host="127.0.0.1", port=port, headless=HEADLESS))
        state["task"] = task
        done, _ = await asyncio.wait({task}, timeout=30)
        if not done:
            print("k=%d HUNG" % k); task.cancel(); break
        exc = task.exception() if not task.cancelled() else asyncio.CancelledError()
        if exc is None:
            b = task.result()
            await b.connection.aclose(); util.get_registered_instances().discard(b); asyncio_atexit.unregister(b._atexit_cleanup)
            await b._cleanup_temporary_profile()
        await asyncio.sleep(0.3)
        left = set(glob.glob(tempfile.gettempdir() + "/uc_*")) - before
        entry = asyncio_atexit._registry.get(asyncio.get_running_loop())
        print(f"k={k} {type(exc).__name__ if exc else 'returned'} ext_alive={ext.poll() is None} targets={targets()} registry={len(util.get_registered_instances())} atexit={len(entry.callbacks) if entry else 0} profiles_left={len(left)}")
        print("   sent:", state["sent"])
        if exc is None or ext.poll() is not None:
            break
        k += 1

try:
    asyncio.run(main())
finally:
    ext.terminate(); ext.wait(10); shutil.rmtree(prof, ignore_errors=True)
