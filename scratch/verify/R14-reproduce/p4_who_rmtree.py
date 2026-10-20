import os, sys, tempfile, asyncio, signal, shutil, traceback, logging
import zendriver as zd
import zendriver.core.browser as zb
SCR = os.path.dirname(os.path.abspath(__file__))
tempfile.tempdir = os.path.join(SCR, "tmp3")
logging.basicConfig(level=logging.WARNING)
logging.getLogger("zendriver.core.browser").setLevel(logging.INFO)
print("zendriver from", zd.__file__)
pids = []
_orig = shutil.rmtree
def spy(path, *a, **k):
    if os.path.basename(str(path)).startswith("uc_") and os.path.isdir(path):
        st = [f"{f.name}:{f.lineno}" for f in traceback.extract_stack()[:-1] if "zendriver" in f.filename]
        print(f"RMTREE {os.path.basename(path)} via {st}")
    return _orig(path, *a, **k)
zb.shutil.rmtree = spy
async def main():
    config = zd.Config(headless=True)
    config()   # docstring-recommended way of inspecting the args
    b1 = await asyncio.wait_for(zd.start(config), 60); pids.append(b1._process.pid)
    print("b1 udd", os.path.basename(b1.config.user_data_dir))
    b2 = zb.Browser(config)
    try:
        await asyncio.wait_for(b2.start(), 60)
    except Exception as e:
        print("b2 failed:", " ".join(str(e).split())[:50])
    if b2._process_pid: pids.append(b2._process_pid)
    print("b1 alive:", b1._process.poll() is None, "b1 profile exists:", os.path.isdir(b1.config.user_data_dir))
    await b1.stop()
try:
    asyncio.run(main())
finally:
    for p in pids:
        try: os.kill(p, 0); print("killing", p); os.kill(p, signal.SIGKILL)
        except ProcessLookupError: pass
