import asyncio, os, sys, signal, shutil, time
import zendriver as zd
print("zendriver from", zd.__file__, "python", sys.version.split()[0])
async def main():
    b = await zd.start(headless=True)
    pid = b._process_pid; udd = b.config.user_data_dir
    try:
        print("targets:", [(t.type_, t.session_id) for t in b.targets])
        os.kill(pid, signal.SIGSTOP)
        task = asyncio.create_task(b.stop())
        done, _ = await asyncio.wait({task}, timeout=8)
        if task in done:
            print("stop returned", task.exception())
        else:
            print("stop() STILL PENDING after 8s"); task.print_stack(file=sys.stdout); task.cancel()
            try: await task
            except asyncio.CancelledError: pass
    finally:
        try: os.kill(pid, signal.SIGCONT); os.kill(pid, signal.SIGKILL)
        except ProcessLookupError: pass
        if b._process: b._process.wait()
        shutil.rmtree(udd, ignore_errors=True)
asyncio.run(main())
