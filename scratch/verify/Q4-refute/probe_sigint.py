"""Simulate Ctrl-C during zd.start(): mode 'group' signals the whole process group (terminal Ctrl-C),
mode 'self' signals only the Python process (kill -INT <pid>, IDE stop, supervisor)."""
import asyncio, json, os, signal, sys, time, pathlib
import psutil
import zendriver as zd
from zendriver.core import util

OUT = pathlib.Path(sys.argv[1]); MODE = sys.argv[2]; DELAY = float(sys.argv[3]) if len(sys.argv) > 3 else 0.03
if os.getpgrp() != os.getpid():
    sys.exit("refusing: not a process group leader (run under setsid)")
spawned = []
orig = util._start_process
def spy(exe, params, is_posix, env=None):
    p = orig(exe, params, is_posix, env=env)
    udd = next((a.split("=", 1)[1] for a in params if a.startswith("--user-data-dir=")), None)
    spawned.append({"pid": p.pid, "udd": udd}); OUT.write_text(json.dumps(spawned))
    loop = asyncio.get_running_loop()
    if MODE == "group":
        loop.call_later(DELAY, os.killpg, os.getpgrp(), signal.SIGINT)
    else:
        loop.call_later(DELAY, os.kill, os.getpid(), signal.SIGINT)
    return p
util._start_process = spy

def alive(pid):
    try: return psutil.Process(pid).status() != psutil.STATUS_ZOMBIE
    except psutil.NoSuchProcess: return False

async def main():
    print("zendriver from", zd.__file__, "python", sys.version.split()[0], "mode", MODE)
    b = await zd.start(headless=True)
    print("start completed before signal; stopping"); await b.stop()

try:
    asyncio.run(main())
except KeyboardInterrupt:
    print("KeyboardInterrupt from asyncio.run")
s = spawned[-1]
for i in range(20):
    if not alive(s["pid"]): break
    time.sleep(0.25)
print(f"after run: pid {s['pid']} alive={alive(s['pid'])} (waited {i*0.25:.2f}s) profile_exists={os.path.exists(s['udd'])}")
