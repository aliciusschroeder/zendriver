import asyncio, logging, sys, tempfile, os, glob
logging.basicConfig(level=logging.DEBUG, format="%(name)s %(message).160s")
logging.getLogger("asyncio").setLevel(logging.WARNING)
import zendriver as zd
from zendriver.core.browser import Browser
print("zendriver:", zd.__file__)
async def main():
    c = zd.Config(browser_executable_path=sys.executable)
    b = Browser(c)
    print("copy _user_data_dir after logged init:", b.config._user_data_dir)
    print(repr(c).splitlines()[:3], "...", [l for l in repr(c).splitlines() if "user_data" in l])
asyncio.run(main())
