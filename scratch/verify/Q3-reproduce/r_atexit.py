"""Reproduce: asyncio.run(main) without stop() -> atexit cleanup fails at to_thread, temp profile leaks."""
import asyncio
import os
import shutil
import sys
import traceback

import zendriver as zd
from zendriver.core.browser import Browser

print("zendriver from", zd.__file__, "python", sys.version.split()[0])

MODE = sys.argv[1] if len(sys.argv) > 1 else "plain"  # plain | ctx | tb
info = {}

if MODE == "tb":
    # capture the traceback from inside _atexit_cleanup without changing behaviour
    orig = Browser._atexit_cleanup

    async def wrapped(self):
        try:
            await orig(self)
        except BaseException:
            traceback.print_exc(file=sys.stdout)
            raise

    Browser._atexit_cleanup = wrapped


async def main():
    if MODE == "ctx":
        async with await zd.start(headless=True) as b:
            info["udd"] = b.config.user_data_dir
            info["pid"] = b._process.pid
            await b.get("about:blank")
        # __aexit__ ran; check whether it already stopped
        print("after async with: _process set:", b._process is not None)
    else:
        b = await zd.start(headless=True)
        info["udd"] = b.config.user_data_dir
        info["pid"] = b._process.pid
        await b.get("about:blank")
        if MODE == "sigint":
            import signal
            print("sending SIGINT to self (Ctrl+C)")
            os.kill(os.getpid(), signal.SIGINT)
            await asyncio.sleep(5)
    print("main done; udd", info["udd"], "pid", info["pid"])


try:
    asyncio.run(main())
except KeyboardInterrupt:
    print("asyncio.run raised KeyboardInterrupt")
udd, pid = info["udd"], info["pid"]
alive = os.path.exists(f"/proc/{pid}")
state = None
if alive:
    with open(f"/proc/{pid}/stat") as f:
        state = f.read().split()[2]
print("after asyncio.run: temp profile exists:", os.path.exists(udd), "| proc alive:", alive, state)
# cleanup what we created
try:
    os.kill(pid, 9)
except ProcessLookupError:
    pass
try:
    os.waitpid(pid, 0)
except ChildProcessError:
    pass
shutil.rmtree(udd, ignore_errors=True)
