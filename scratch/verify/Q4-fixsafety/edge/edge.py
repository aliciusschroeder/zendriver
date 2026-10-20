import asyncio, os, sys, shutil, gc
import zendriver as zd
from zendriver.core import util
print("zendriver from", zd.__file__)
FAKE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fake-chrome")
spawned = []
orig = util._start_process
def spy(*a, **k):
    p = orig(*a, **k); spawned.append(p); return p
util._start_process = spy
def pdir(p):
    return [a.split("=",1)[1] for a in p.args if a.startswith("--user-data-dir=")][0]
def report(tag):
    p = spawned[-1]
    print(f"{tag}: poll={p.poll()} profile_exists={os.path.exists(pdir(p))} registered={len(util.get_registered_instances())}")

async def e1_close():
    coro = zd.start(browser_executable_path=FAKE)
    t = asyncio.ensure_future(coro)
    await asyncio.sleep(0.3)
    try:
        coro.close()
        print("E1 coro.close() returned normally")
    except BaseException as e:
        print("E1 coro.close() raised", type(e).__name__, e)
    await asyncio.sleep(0.5)
    report("E1")

async def e2_double_cancel():
    t = asyncio.ensure_future(zd.start(browser_executable_path=FAKE))
    await asyncio.sleep(0.3)
    t.cancel()
    await asyncio.sleep(0.01)  # cleanup started (stop -> terminate -> sleep loop)
    t.cancel()
    try:
        await asyncio.wait_for(t, 10)
    except BaseException as e:
        print("E2 task ended with", type(e).__name__)
    await asyncio.sleep(0.5)
    report("E2")

async def main():
    which = sys.argv[1]
    await {"e1": e1_close, "e2": e2_double_cancel}[which]()

try:
    asyncio.run(main())
finally:
    for p in spawned:
        if p.poll() is None:
            p.kill(); p.wait()
        shutil.rmtree(pdir(p), ignore_errors=True)
