import asyncio, os, signal, shutil
import zendriver as zd

async def main():
    b = await zd.start(headless=True)
    udd = b.config.user_data_dir
    pid = b._process_pid
    proc = b._process
    await b.get("about:blank")
    os.kill(pid, signal.SIGSTOP)   # browser wedged (e.g. frozen / blocked on a full stderr pipe)
    t = asyncio.create_task(b.stop())
    done, _ = await asyncio.wait({t}, timeout=12)
    if not done:
        print("stop() still running after 12s; stuck at:")
        t.print_stack()
        print("process still alive:", proc.poll() is None)
        t.cancel()
    else:
        print("stop finished", t.exception())
    os.kill(pid, signal.SIGKILL); proc.wait()
    shutil.rmtree(udd, ignore_errors=True)

asyncio.run(main())
