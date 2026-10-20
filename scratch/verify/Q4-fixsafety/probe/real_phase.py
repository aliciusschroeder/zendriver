import asyncio, os, sys, json, time
import zendriver as zd
from zendriver.core import util
from zendriver.core.browser import Browser
print("zendriver from", zd.__file__)
spawned = []
orig = util._start_process
def spy(*a, **k):
    p = orig(*a, **k); spawned.append(p); return p
util._start_process = spy
def pdir(p):
    return [a.split("=",1)[1] for a in p.args if a.startswith("--user-data-dir=")][0]

phase = sys.argv[1]
mode = sys.argv[2]  # "hang" -> cancelled by wait_for; "raise" -> raises RuntimeError
orig_m = getattr(Browser, phase)
async def patched(self, *a, **k):
    await orig_m(self, *a, **k) if phase == "update_targets" and getattr(self, "_once", False) else None
    self._once = True
    if mode == "hang":
        await asyncio.sleep(30)
    raise RuntimeError("injected failure in " + phase)
setattr(Browser, phase, patched)

async def main():
    t0 = time.monotonic()
    try:
        b = await asyncio.wait_for(zd.start(headless=True), 3)
        print("started?!"); await b.stop()
    except BaseException as e:
        print("start raised", type(e).__name__, e)
    p = spawned[-1]
    print(f"phase={phase} mode={mode} elapsed={time.monotonic()-t0:.2f}s pid={p.pid} poll={p.poll()} profile_exists={os.path.exists(pdir(p))} registered={len(util.get_registered_instances())}")
asyncio.run(main())
alive = [p.pid for p in spawned if p.poll() is None]
print("alive after asyncio.run:", alive)
with open(os.environ["OUTF"], "a") as f:
    f.write(json.dumps({"pids": [p.pid for p in spawned], "dirs": [pdir(p) for p in spawned]}) + "\n")
