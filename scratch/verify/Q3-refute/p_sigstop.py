import asyncio, os, sys, signal, shutil, time
import zendriver as zd
print("zendriver from", zd.__file__, "python", sys.version.split()[0])
ATTACH = sys.argv[1] == "attach"
WAIT = float(sys.argv[2])
async def main():
    b = await zd.start(headless=True)
    pid = b._process_pid; udd = b.config.user_data_dir
    print("pid", pid, "udd", udd)
    try:
        tab = await b.get("about:blank")
        if ATTACH:
            await tab.evaluate("1")
        print("tab session:", tab.session_id, "targets:", len(b.targets))
        os.kill(pid, signal.SIGSTOP)
        t0 = time.monotonic()
        task = asyncio.create_task(b.stop())
        done, _ = await asyncio.wait({task}, timeout=WAIT)
        if task in done:
            print("stop() returned after %.1fs exc=%r" % (time.monotonic()-t0, task.exception()))
        else:
            print("stop() STILL PENDING after %.1fs" % (time.monotonic()-t0))
            task.print_stack(file=sys.stdout)
            st = open(f"/proc/{pid}/stat").read().split()[2]
            print("process state:", st, "profile exists:", os.path.exists(udd))
            # what happens if the caller bounds it with wait_for?
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                print("stop() cancelled")
            st = open(f"/proc/{pid}/stat").read().split()[2]
            print("after cancel: process state:", st, "profile exists:", os.path.exists(udd), "b._process:", b._process)
    finally:
        try:
            os.kill(pid, signal.SIGCONT); os.kill(pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        if b._process:
            b._process.wait()
        shutil.rmtree(udd, ignore_errors=True)
        print("cleanup done")
asyncio.run(main())
