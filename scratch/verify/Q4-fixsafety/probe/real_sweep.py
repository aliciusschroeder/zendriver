import asyncio, os, sys, json, time
import zendriver as zd
from zendriver.core import util
print("zendriver from", zd.__file__)
spawned = []
orig = util._start_process
def spy(*a, **k):
    p = orig(*a, **k); spawned.append(p); return p
util._start_process = spy
from zendriver.core.browser import Browser
insts = []
_oi = Browser.__init__
def _ni(self, *a, **k):
    _oi(self, *a, **k); insts.append(self)
Browser.__init__ = _ni

def pdir(p):
    return [a.split("=",1)[1] for a in p.args if a.startswith("--user-data-dir=")][0]

async def one(T):
    n = len(spawned)
    t0 = time.monotonic()
    phase = None
    try:
        b = await asyncio.wait_for(zd.start(headless=True), T)
        res = "started"
        await b.stop()
    except asyncio.TimeoutError:
        res = "timeout"
    el = time.monotonic() - t0
    p = spawned[n]
    print(f"T={T:<5} {res:8} elapsed={el:.2f}s pid={p.pid} poll={p.poll()} profile_exists={os.path.exists(pdir(p))} registered={len(util.get_registered_instances())} conn={insts[-1].connection is not None} targets={len(insts[-1].targets)} ua={insts[-1]._headless_user_agent is not None}")

async def main():
    for T in [float(x) for x in sys.argv[1:]]:
        await one(T)

asyncio.run(main())
alive = [p.pid for p in spawned if p.poll() is None]
print("alive after asyncio.run:", alive)
with open(os.environ["OUTF"], "w") as f:
    json.dump({"pids": [p.pid for p in spawned], "dirs": [pdir(p) for p in spawned]}, f)
