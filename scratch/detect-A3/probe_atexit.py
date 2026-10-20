import asyncio, os, sys
import zendriver as zd

state = {}
async def main():
    b = await zd.start(headless=True)
    state["udd"] = b.config.user_data_dir
    state["pid"] = b._process_pid
    print("udd", state["udd"], "exists", os.path.exists(state["udd"]))
    await b.get("about:blank")
    # no stop(): rely on the atexit cleanup

asyncio.run(main())
print("after asyncio.run: temp profile exists:", os.path.exists(state["udd"]))
try:
    os.kill(state["pid"], 0)
    # might be a zombie
    with open(f"/proc/{state['pid']}/status") as f:
        st=[l for l in f if l.startswith("State")]
    print("chrome pid still present:", st)
except ProcessLookupError:
    print("chrome pid gone")
