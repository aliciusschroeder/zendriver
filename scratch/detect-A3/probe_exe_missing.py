import asyncio, glob, shutil
import zendriver as zd

async def main():
    before = set(glob.glob("/tmp/uc_*"))
    for i in range(3):
        try:
            await zd.start(browser_executable_path="/nonexistent/chrome")
        except FileNotFoundError as e:
            pass
    leaked = set(glob.glob("/tmp/uc_*")) - before
    print("temp profiles leaked by 3 failed starts:", len(leaked), sorted(leaked))
    for d in leaked: shutil.rmtree(d, ignore_errors=True)

asyncio.run(main())
