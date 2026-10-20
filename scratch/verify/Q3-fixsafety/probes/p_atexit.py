import asyncio, os, shutil, sys
import zendriver as zd
print("zendriver from", zd.__file__)
d = {}
async def main():
    b = await zd.start(headless=True)
    await b.get("about:blank")
    d["udd"] = b.config.user_data_dir
    d["pid"] = b._process.pid

asyncio.run(main())
alive = True
try:
    os.kill(d["pid"], 0)
except ProcessLookupError:
    alive = False
print("after asyncio.run: profile exists:", os.path.exists(d["udd"]), "pid alive(maybe zombie):", alive)
try:
    os.kill(d["pid"], 9)
except ProcessLookupError:
    pass
shutil.rmtree(d["udd"], ignore_errors=True)
