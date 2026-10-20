import asyncio, os, sys
import zendriver as zd
async def main():
    b = await zd.start(headless=True)
    print(b._process_pid, b.config.user_data_dir, flush=True)
    await b.get("about:blank")
    await asyncio.sleep(30)
try:
    asyncio.run(main())
except KeyboardInterrupt:
    print("KeyboardInterrupt", file=sys.stderr)
