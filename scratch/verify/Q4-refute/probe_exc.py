"""Exception after spawn: (a) Chrome dies right after /json/version answered (crash-like),
(b) an exception raised later in start() while Chrome is alive (injected)."""
import asyncio, json, os, signal, sys, pathlib
import psutil
import zendriver as zd
from zendriver.core import util
from zendriver.core.browser import Browser

OUT = pathlib.Path(sys.argv[1]); MODE = sys.argv[2]
spawned = []
orig = util._start_process
def spy(exe, params, is_posix, env=None):
    p = orig(exe, params, is_posix, env=env)
    udd = next((a.split("=", 1)[1] for a in params if a.startswith("--user-data-dir=")), None)
    spawned.append({"pid": p.pid, "udd": udd}); OUT.write_text(json.dumps(spawned)); return p
util._start_process = spy

if MODE == "crash":
    orig_tc = Browser.test_connection
    async def tc(self):
        ok = await orig_tc(self)
        if ok:
            os.kill(self._process.pid, signal.SIGKILL); self._process.wait()
        return ok
    Browser.test_connection = tc
else:
    async def boom(self):
        raise RuntimeError("injected failure in _read_headless_user_agent")
    Browser._read_headless_user_agent = boom

def alive(pid):
    try: return psutil.Process(pid).status() != psutil.STATUS_ZOMBIE
    except psutil.NoSuchProcess: return False

async def main():
    print("zendriver from", zd.__file__, "mode", MODE)
    try:
        await asyncio.wait_for(zd.start(headless=True), 30)
        print("start returned normally")
    except Exception as e:
        print("start raised", type(e).__name__, str(e)[:80])
    s = spawned[-1]
    print(f"  pid alive={alive(s['pid'])} profile_exists={os.path.exists(s['udd'])} registered={len(util.get_registered_instances())}")
asyncio.run(main())
s = spawned[-1]; print(f"after asyncio.run: pid alive={alive(s['pid'])} profile_exists={os.path.exists(s['udd'])}")
