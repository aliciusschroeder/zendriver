import os, sys, glob, tempfile, asyncio, signal
import zendriver as zd
SCR = os.path.dirname(os.path.abspath(__file__))
tempfile.tempdir = os.path.join(SCR, "tmp3")   # python-side mkdtemp only; chrome's env TMPDIR untouched
print("zendriver from", zd.__file__, "py", sys.version.split()[0])
MODE = sys.argv[1]
pids = []
def alive(b): return b._process is not None and b._process.poll() is None

async def try_start(config, name):
    b = None
    try:
        b = await asyncio.wait_for(zd.start(config), 60)
        pids.append(b._process.pid)
        print(f"{name}: started pid={b._process.pid} udd={b.config.user_data_dir} custom={b.config.uses_custom_data_dir}")
    except Exception as e:
        print(f"{name}: start FAILED: {type(e).__name__}: {' '.join(str(e).split())[:70]}")
    return b

async def main():
    config = zd.Config(headless=True)
    print("template _user_data_dir before:", config._user_data_dir)
    if MODE == "repr":
        print(config)  # just printing the template
    print("template _user_data_dir after:", config._user_data_dir)
    b1 = await try_start(config, "b1")
    print("b1 profile exists:", os.path.isdir(b1.config.user_data_dir), "entries:", len(os.listdir(b1.config.user_data_dir)))
    b2 = await try_start(config, "b2")
    print("b1 still running:", alive(b1), " b1 profile exists:", os.path.isdir(b1.config.user_data_dir))
    # is b1 still usable?
    try:
        tab = await asyncio.wait_for(b1.get("data:text/html,<title>hello</title>"), 20)
        print("b1 usable after b2 attempt, title:", await asyncio.wait_for(tab.evaluate("document.title"), 10))
    except Exception as e:
        print("b1 use failed:", type(e).__name__, e)
    if b2 is not None:
        print("same udd:", b1.config.user_data_dir == b2.config.user_data_dir)
        await b2.stop()
        print("after b2.stop: b1 running:", alive(b1), "b1 profile exists:", os.path.isdir(b1.config.user_data_dir))
    await b1.stop()
    print("after b1.stop: b1 profile exists:", os.path.isdir(b1.config.user_data_dir))
    print("leftover in tmp3:", os.listdir(tempfile.tempdir))

try:
    asyncio.run(main())
finally:
    for p in pids:
        try:
            os.kill(p, 0); print("killing leftover pid", p); os.kill(p, signal.SIGKILL)
        except ProcessLookupError:
            pass
