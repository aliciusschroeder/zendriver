import asyncio, os, sys, json
import zendriver as zd
from zendriver.core import util
print("zendriver from", zd.__file__)
spawned = []
orig = util._start_process
def spy(*a, **k):
    p = orig(*a, **k)
    spawned.append(p)
    return p
util._start_process = spy

T = float(sys.argv[1]) if len(sys.argv) > 1 else 0.3

async def main():
    try:
        b = await asyncio.wait_for(zd.start(headless=True), T)
        print("started normally (timeout too large)")
        await b.stop()
    except asyncio.TimeoutError:
        print("start timed out after", T)
    regs = list(util.get_registered_instances())
    print("registered instances:", len(regs))
    for b in regs:
        print(" pid", b._process_pid, "alive", b._process.poll() is None if b._process else None,
              "info", bool(b.info), "connection", b.connection,
              "profile", b.config.user_data_dir, os.path.exists(b.config.user_data_dir))

asyncio.run(main())
for p in spawned:
    print("after asyncio.run pid", p.pid, "poll", p.poll())
out = [{"pid": p.pid} for p in spawned]
regs = list(util.get_registered_instances())
for b in regs:
    out.append({"dir": b.config.user_data_dir})
with open(os.environ["OUTF"], "w") as f:
    json.dump(out, f)
