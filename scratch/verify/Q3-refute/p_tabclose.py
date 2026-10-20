import asyncio, os, sys, signal, shutil
import zendriver as zd
print("zendriver from", zd.__file__, "python", sys.version.split()[0])
async def main():
    b = await zd.start(headless=True)
    pid = b._process_pid; udd = b.config.user_data_dir
    try:
        tab = await b.get("about:blank")
        os.kill(pid, signal.SIGSTOP)
        task = asyncio.create_task(tab.close())
        done, _ = await asyncio.wait({task}, timeout=13)
        if task in done: print("tab.close returned/raised:", repr(task.exception()))
        else:
            print("tab.close STILL PENDING after 13s (docstring promises TimeoutError at 10s)"); task.print_stack(file=sys.stdout); task.cancel()
            try: await task
            except asyncio.CancelledError: pass
    finally:
        try: os.kill(pid, signal.SIGCONT); os.kill(pid, signal.SIGKILL)
        except ProcessLookupError: pass
        if b._process: b._process.wait()
        shutil.rmtree(udd, ignore_errors=True)
asyncio.run(main())
