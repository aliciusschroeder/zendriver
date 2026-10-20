import asyncio, os, sys, glob, tempfile, shutil
import zendriver as zd
print("zendriver file:", zd.__file__, "py", sys.version.split()[0])
T = tempfile.gettempdir()
def dirs(): return sorted(glob.glob(os.path.join(T, "uc_*")))
DO_REPR = sys.argv[1] == "repr"

async def main():
    config = zd.Config(headless=True, browser_connection_max_tries=40)
    if DO_REPR:
        repr(config)
    print("template _user_data_dir:", config._user_data_dir)
    b1 = await zd.start(config)
    print("b1 udd", b1.config.user_data_dir, "pid", b1._process_pid)
    b2 = None
    try:
        b2 = await zd.start(config)
        print("b2 udd", b2.config.user_data_dir, "pid", b2._process_pid)
    except Exception as e:
        print("b2 start failed:", type(e).__name__, [l.strip() for l in str(e).splitlines() if l.strip()][1:2])
    print("b1 process alive:", b1._process.poll() is None, "b1 profile exists:", os.path.isdir(b1.config.user_data_dir))
    # does b1 still work?
    try:
        tab = await asyncio.wait_for(b1.get("about:blank"), 15)
        print("b1 still usable: ok")
    except Exception as e:
        print("b1 get failed:", type(e).__name__, e)
    if b2:
        await b2.stop()
        print("after b2.stop: b1 profile exists:", os.path.isdir(b1.config.user_data_dir), "b1 alive", b1._process.poll() is None)
    await b1.stop()
    print("leftover uc dirs:", dirs())
    if DO_REPR and config._user_data_dir:
        shutil.rmtree(config._user_data_dir, ignore_errors=True)

asyncio.run(asyncio.wait_for(main(), 100))
