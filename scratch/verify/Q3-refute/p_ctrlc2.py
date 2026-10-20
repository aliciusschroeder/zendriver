import asyncio, os, sys, signal, time
import zendriver as zd
LOOP = None
def dump(signum, frame):
    print("=== SIGUSR1 dump at", time.strftime("%X"), file=sys.stderr)
    for t in asyncio.all_tasks(LOOP):
        t.print_stack(file=sys.stderr)
    sys.stderr.flush()
signal.signal(signal.SIGUSR1, dump)
async def main():
    global LOOP
    LOOP = asyncio.get_running_loop()
    b = await zd.start(headless=True)
    print(b._process_pid, b.config.user_data_dir, flush=True)
    await b.get("about:blank")
    await asyncio.sleep(30)
try:
    asyncio.run(main())
except KeyboardInterrupt:
    print("KeyboardInterrupt", file=sys.stderr)
print("python exiting", file=sys.stderr)
