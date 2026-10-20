import asyncio, os, signal, shutil, sys, time
import zendriver as zd
print("zendriver from", zd.__file__)

async def main():
    b = await zd.start(headless=True)
    tab = await b.get("about:blank")
    await tab.evaluate("1")
    pid = b._process.pid
    udd = b.config.user_data_dir
    print("session attached:", tab.session_id is not None)
    os.kill(pid, signal.SIGSTOP)
    t0 = time.monotonic()
    t = asyncio.create_task(b.stop())
    done, _ = await asyncio.wait({t}, timeout=float(os.environ.get("WAIT", "10")))
    print("stop done within WAIT:", bool(done), "elapsed %.1f" % (time.monotonic() - t0))
    if not done:
        t.print_stack(file=sys.stdout)
        t.cancel()
        try:
            await t
        except BaseException as e:
            print("after cancel:", type(e).__name__)
    else:
        print("stop result exc:", t.exception())
    alive = True
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        alive = False
    print("process alive after:", alive and (b._process is None or b._process.poll() is None), "profile exists:", os.path.exists(udd))
    # cleanup what we started
    try:
        os.kill(pid, signal.SIGCONT); os.kill(pid, signal.SIGKILL)
    except ProcessLookupError:
        pass
    if b._process: b._process.wait()
    shutil.rmtree(udd, ignore_errors=True)

asyncio.run(main())
