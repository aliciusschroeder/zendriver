"""SIGSTOP Chrome; bound stop() with wait_for; return from asyncio.run; is anything cleaned at exit?
mode 'tabclose': instead measure Tab.close() on a frozen Chrome (docstring promises 10s TimeoutError)."""
import asyncio, os, shutil, signal, sys, time
import zendriver as zd
print("zendriver from", zd.__file__, "python", sys.version.split()[0])
MODE = sys.argv[1] if len(sys.argv) > 1 else "stop"
info = {}

async def main():
    b = await zd.start(headless=True)
    info["pid"] = pid = b._process.pid
    info["udd"] = b.config.user_data_dir
    tab = await b.get("about:blank")
    await tab.evaluate("1")
    os.kill(pid, signal.SIGSTOP)
    if MODE == "tabclose":
        t0 = time.monotonic()
        t = asyncio.create_task(tab.close())
        done, _ = await asyncio.wait({t}, timeout=25)
        print(f"tab.close() done={t in done} after {time.monotonic()-t0:.1f}s",
              (repr(t.exception()) if t in done else ""))
        if t not in done:
            c = t.get_coro(); chain = []
            while c is not None and hasattr(c, "cr_frame"):
                if c.cr_frame: chain.append(f"{c.cr_frame.f_code.co_qualname}:{c.cr_frame.f_lineno}")
                c = getattr(c, "cr_await", None)
            print("stuck at:", " -> ".join(chain))
            t.cancel(); await asyncio.gather(t, return_exceptions=True)
        os.kill(pid, signal.SIGCONT); os.kill(pid, signal.SIGKILL)
        return
    try:
        await asyncio.wait_for(b.stop(), 5)
        print("stop returned")
    except asyncio.TimeoutError:
        print("wait_for(stop(), 5) -> TimeoutError; returning from main without further cleanup")

asyncio.run(main())
pid, udd = info["pid"], info["udd"]
alive = os.path.exists(f"/proc/{pid}")
st = open(f"/proc/{pid}/stat").read().split()[2] if alive else None
print("after asyncio.run (atexit hooks ran): proc alive:", alive, "state:", st, "| profile exists:", os.path.exists(udd))
try:
    os.kill(pid, signal.SIGCONT); os.kill(pid, signal.SIGKILL)
except ProcessLookupError:
    pass
try:
    os.waitpid(pid, 0)
except ChildProcessError:
    pass
shutil.rmtree(udd, ignore_errors=True)
print("cleaned up; proc alive:", os.path.exists(f"/proc/{pid}"))
