import asyncio, os, sys, signal, shutil, time
import zendriver as zd
print("zendriver from", zd.__file__, "python", sys.version.split()[0])
async def main():
    b = await zd.start(headless=True)
    pid = b._process_pid; udd = b.config.user_data_dir
    try:
        tab = await b.get("about:blank")
        ev = asyncio.create_task(tab.evaluate("while(true){}"))
        await asyncio.sleep(1)
        t0 = time.monotonic()
        task = asyncio.create_task(b.stop())
        done, _ = await asyncio.wait({task}, timeout=15)
        if task in done: print("stop() finished in %.2fs exc=%r" % (time.monotonic()-t0, task.exception()))
        else:
            print("stop() pending after 15s"); task.print_stack(file=sys.stdout); task.cancel()
        print("evaluate task:", ev.done() and repr(ev.exception()))
        print("profile exists:", os.path.exists(udd), "process set:", b._process is not None)
    finally:
        try: os.kill(pid, signal.SIGKILL)
        except ProcessLookupError: pass
        if b._process: b._process.wait()
        shutil.rmtree(udd, ignore_errors=True)
asyncio.run(main())
