import asyncio, os, glob, sys
import psutil
import zendriver as zd
from zendriver.core import util

T = float(sys.argv[1])
before = set(glob.glob("/tmp/uc_*"))
pids = {}
async def main():
    try:
        await asyncio.wait_for(zd.start(headless=True), T)
        print("started within timeout")
    except asyncio.TimeoutError:
        print("start timed out")
    insts = list(util.get_registered_instances())
    print("registered instances:", len(insts))
    for b in insts:
        pids[b._process_pid] = b.config.user_data_dir
        print("  pid", b._process_pid, "alive", b._process and b._process.poll() is None, "info", bool(b.info), "connection", b.connection)

asyncio.run(main())
after = set(glob.glob("/tmp/uc_*")) - before
print("new temp profiles left:", after)
for pid in pids:
    print("pid", pid, "running after asyncio.run:", psutil.pid_exists(pid) and psutil.Process(pid).status())
