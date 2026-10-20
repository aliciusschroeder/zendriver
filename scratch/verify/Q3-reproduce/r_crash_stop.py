"""Reproduce: Chrome dies, stop() right after raises ConnectionClosedError from Tab.aclose and leaks."""
import asyncio
import os
import shutil
import sys
import traceback

import zendriver as zd

print("zendriver from", zd.__file__, "python", sys.version.split()[0])

DELAY = float(sys.argv[1]) if len(sys.argv) > 1 else 0.0


async def main():
    b = await zd.start(headless=True)
    pid = b._process.pid
    udd = b.config.user_data_dir
    try:
        tab = await b.get("about:blank")
        await tab.evaluate("1")
        b._process.kill()
        if DELAY:
            await asyncio.sleep(DELAY)
        try:
            await asyncio.wait_for(b.stop(), 20)
            res = "ok"
        except BaseException as e:
            res = f"RAISED {type(e).__name__}: {e}"
            tb = traceback.extract_tb(e.__traceback__)
            res += " | tb: " + " -> ".join(f"{fr.name}:{fr.lineno}" for fr in tb)
        print(f"delay={DELAY} stop {res} | _process still set: {b._process is not None} | "
              f"profile exists: {os.path.exists(udd)} | conn.closed: {b.connection.closed if b.connection else None}")
    finally:
        try:
            os.kill(pid, 9)
        except ProcessLookupError:
            pass
        try:
            os.waitpid(pid, 0)
        except ChildProcessError:
            pass
        if b.connection and b.connection.websocket is not None:
            await b.connection.aclose()
        shutil.rmtree(udd, ignore_errors=True)


asyncio.run(asyncio.wait_for(main(), 60))
