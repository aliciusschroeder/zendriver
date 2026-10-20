import asyncio, os, sys, signal, shutil, time
import zendriver as zd
import zendriver.core.connection as zc
zc.PING_TIMEOUT = 3   # shorten keepalive bound (real default 900s, ping_interval default 20s)
print("zendriver from", zd.__file__, "python", sys.version.split()[0])
async def main():
    b = await zd.start(headless=True)
    pid = b._process_pid; udd = b.config.user_data_dir
    try:
        tab = await b.get("about:blank")
        os.kill(pid, signal.SIGSTOP)
        t0 = time.monotonic()
        task = asyncio.create_task(b.stop())
        done, _ = await asyncio.wait({task}, timeout=60)
        el = time.monotonic()-t0
        if task in done:
            print("stop() finished after %.1fs exc=%r" % (el, task.exception()))
        else:
            print("still pending after %.1fs" % el); task.print_stack(file=sys.stdout); task.cancel()
        st = open(f"/proc/{pid}/stat").read().split()[2]
        print("process state:", st, "profile exists:", os.path.exists(udd), "b._process:", b._process is not None)
    finally:
        try:
            os.kill(pid, signal.SIGCONT); os.kill(pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        if b._process: b._process.wait()
        shutil.rmtree(udd, ignore_errors=True)
        print("cleanup done")
asyncio.run(main())
