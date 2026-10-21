"""launch chromium via zd.start(); cancel (or fail) at the k-th cdp message.
check: process gone, profile removed, registry/atexit clean, stderr thread exited."""
import asyncio, glob, json, logging, os, shutil, subprocess, sys, tempfile, time, threading
import asyncio_atexit, websockets, psutil
import zendriver as zd
from zendriver.core import util

logging.basicConfig(level=logging.ERROR, format="LOG %(levelname)s %(name)s: %(message)s")
CHROME = shutil.which("chromium")
MODE = sys.argv[1] if len(sys.argv) > 1 else "cancel"
real_connect = websockets.connect
real_start_process = util._start_process
state = {"k": 0, "n": 0, "task": None, "sent": [], "fired": False, "procs": []}

def start_process(*a, **k):
    p = real_start_process(*a, **k)
    state["procs"].append(p)
    return p
util._start_process = start_process

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
    print("python", sys.version.split()[0], zd.__file__, "mode", MODE)
    k = 1
    while True:
        state.update(k=k, n=0, sent=[], fired=False, procs=[])
        before = set(glob.glob(tempfile.gettempdir() + "/uc_*"))
        t0 = time.monotonic()
        task = asyncio.ensure_future(zd.start(headless=True, sandbox=False, browser_executable_path=CHROME))
        state["task"] = task
        done, _ = await asyncio.wait({task}, timeout=60)
        if not done:
            print("k=%d HUNG" % k); task.cancel(); break
        dt = time.monotonic() - t0
        exc = task.exception() if not task.cancelled() else asyncio.CancelledError()
        if exc is None:
            await task.result().stop()
        p = state["procs"][0]
        tail = util._stderr_tails.get(p)
        await asyncio.sleep(0.3)
        left = set(glob.glob(tempfile.gettempdir() + "/uc_*")) - before
        entry = asyncio_atexit._registry.get(asyncio.get_running_loop())
        print(f"k={k} {type(exc).__name__ if exc else 'returned'} in {dt:.2f}s rc={p.poll()} thread_alive={tail._thread.is_alive() if tail else None} registry={len(util.get_registered_instances())} atexit={len(entry.callbacks) if entry else 0} profiles_left={len(left)}")
        print("   sent:", state["sent"][-4:])
        if p.poll() is None:
            p.kill(); p.wait()
        if exc is None:
            break
        k += 1
    print("threads:", [t.name for t in threading.enumerate()])

asyncio.run(main())
