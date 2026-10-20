import asyncio, os, sys, glob, tempfile
import zendriver as zd
print("zendriver from", zd.__file__, "python", sys.version.split()[0])
d = {}
async def main():
    b = await zd.start(headless=True)
    d['udd'] = b.config.user_data_dir
    d['pid'] = b._process_pid
    tab = await b.get("about:blank")
    await tab.evaluate("1")
    d['b'] = b
asyncio.run(main())
print("after asyncio.run: profile exists:", os.path.exists(d['udd']))
try:
    os.kill(d['pid'], 0)
    st = open(f"/proc/{d['pid']}/stat").read().split()[2]
    print("process", d['pid'], "state", st)
except ProcessLookupError:
    print("process gone")
import shutil
if os.path.exists(d['udd']):
    shutil.rmtree(d['udd'], ignore_errors=True)
    print("removed leaked profile manually")
