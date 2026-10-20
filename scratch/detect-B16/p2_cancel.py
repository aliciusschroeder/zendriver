import asyncio, os, subprocess, json
import zendriver as zd
from zendriver.core import util

leaked = []
async def main():
    for delay in (0.1, 0.25):
        try:
            await asyncio.wait_for(zd.start(headless=True), delay)
            print("started within", delay)
        except asyncio.TimeoutError:
            print("timed out after", delay)
        await asyncio.sleep(1.0)
    for b in list(util.get_registered_instances()):
        print("  registered browser pid", b._process_pid, "running?", not b.stopped, "dir exists?", os.path.isdir(b.config.user_data_dir), b.config.user_data_dir)
        leaked.append((b._process_pid, b.config.user_data_dir))

asyncio.run(main())
json.dump(leaked, open("leaked.json", "w"))
