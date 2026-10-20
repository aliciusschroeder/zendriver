import asyncio, os, glob, tempfile, sys
import zendriver as zd
from zendriver.core.browser import Browser
print("zendriver file:", zd.__file__)
T = tempfile.gettempdir()
print("tempdir:", T)
def dirs(): return sorted(glob.glob(os.path.join(T, "uc_*")))

async def main():
    # 1. repr materializes
    c = zd.Config(headless=True, browser_executable_path=sys.executable)
    print("before repr _user_data_dir:", c._user_data_dir, "dirs:", dirs())
    repr(c)
    print("after repr _user_data_dir:", c._user_data_dir, "custom:", c.uses_custom_data_dir, "dirs:", dirs())
    b1 = Browser(c); b2 = Browser(c)
    print("deepcopies share path:", b1.config.user_data_dir == b2.config.user_data_dir, b1.config.user_data_dir)
    import shutil; shutil.rmtree(c._user_data_dir, ignore_errors=True)

    # 2. without repr: Browser.__init__ eagerly formats vars(self) -> materializes on copy
    c2 = zd.Config(headless=True, browser_executable_path=sys.executable)
    b3 = Browser(c2)
    print("template after Browser():", c2._user_data_dir, "copy:", b3.config._user_data_dir)
    shutil.rmtree(b3.config._user_data_dir, ignore_errors=True) if b3.config._user_data_dir else None

    # 3. bad exe leak
    before = set(dirs())
    for _ in range(3):
        try:
            await zd.start(browser_executable_path="/nonexistent/chrome", headless=True)
        except FileNotFoundError:
            pass
    leaked = sorted(set(dirs()) - before)
    print("bad exe leaked:", len(leaked), leaked)
    for d in leaked: shutil.rmtree(d, ignore_errors=True)

    # 4. connect-existing failure leak
    before = set(dirs())
    import socket
    s = socket.socket(); s.bind(("127.0.0.1", 0)); port = s.getsockname()[1]; s.close()
    try:
        await zd.start(host="127.0.0.1", port=port, headless=True, browser_executable_path=sys.executable, browser_connection_max_tries=0)
    except Exception as e:
        print("connect existing failed:", type(e).__name__, str(e).strip().splitlines()[1] if str(e).strip() else e)
    leaked = sorted(set(dirs()) - before)
    print("connect-existing leaked:", len(leaked), leaked)
    for d in leaked: shutil.rmtree(d, ignore_errors=True)

asyncio.run(asyncio.wait_for(main(), 60))
