import asyncio, sys, shutil
import zendriver as zd
from zendriver.core.browser import Browser
print("zendriver:", zd.__file__)
async def main():
    for how in ("call", "read"):
        c = zd.Config(browser_executable_path=sys.executable)
        if how == "call": c()
        else: c.user_data_dir
        b1, b2 = Browser(c), Browser(c)
        print(how, "-> shared profile:", b1.config.user_data_dir == b2.config.user_data_dir)
        shutil.rmtree(c._user_data_dir, ignore_errors=True)
asyncio.run(main())
