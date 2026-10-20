import asyncio, os, sys
import zendriver
from zendriver import cdp
HERE = os.path.dirname(os.path.abspath(__file__))
print("python", sys.version.split()[0], "zendriver from", zendriver.__file__)
async def main():
    d = os.path.join(HERE, "profiles", "lastwins"); os.makedirs(d, exist_ok=True)
    b = await zendriver.start(headless=True, user_data_dir=d, user_agent="FromConfigAttr/1.0",
                              browser_args=["--user-agent=FromBrowserArgs/1.0"])
    try:
        argv = open(f"/proc/{b._process_pid}/cmdline","rb").read().split(b"\0")
        print("argv user-agent entries:", [a.decode() for a in argv if a.startswith(b"--user-agent")])
        _, _, _, ua, _ = await b.connection.send(cdp.browser.get_version())
        print("Browser.getVersion userAgent:", ua)
    finally:
        await b.stop()
asyncio.run(main())
