"""Reproduce: two concurrent Browser.stop() calls -> AttributeError 'NoneType' has no attribute 'poll'."""
import asyncio
import os
import shutil
import sys
import traceback

import zendriver as zd

print("zendriver from", zd.__file__, "python", sys.version.split()[0])
RUNS = int(sys.argv[1]) if len(sys.argv) > 1 else 5


import random
STAGGER = float(os.environ.get("STAGGER", "0"))


async def delayed(b):
    if STAGGER:
        await asyncio.sleep(random.uniform(0, STAGGER))
    return await b.stop()


async def one():
    b = await zd.start(headless=True)
    pid = b._process.pid
    udd = b.config.user_data_dir
    try:
        await b.get("about:blank")
        res = await asyncio.wait_for(
            asyncio.gather(b.stop(), delayed(b), return_exceptions=True), 30
        )
        out = []
        for r in res:
            if isinstance(r, BaseException):
                tb = traceback.extract_tb(r.__traceback__)
                out.append(f"{type(r).__name__}({r}) @ " + "->".join(f"{f.name}:{f.lineno}" for f in tb))
            else:
                out.append(repr(r))
        print("results:", out, "| profile exists:", os.path.exists(udd))
    finally:
        try:
            os.kill(pid, 9)
        except ProcessLookupError:
            pass
        try:
            os.waitpid(pid, 0)
        except ChildProcessError:
            pass
        shutil.rmtree(udd, ignore_errors=True)


async def main():
    for _ in range(RUNS):
        await one()


asyncio.run(asyncio.wait_for(main(), 110))
