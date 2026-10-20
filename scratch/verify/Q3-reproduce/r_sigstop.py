"""Reproduce: Browser.stop() hangs on a frozen (SIGSTOP) Chrome, never reaching terminate/kill."""
import asyncio
import os
import signal
import sys

import zendriver as zd

print("zendriver from", zd.__file__, "python", sys.version.split()[0])

MODE = sys.argv[1] if len(sys.argv) > 1 else "attached"  # attached | noattach


async def main():
    b = await zd.start(headless=True)
    pid = b._process.pid
    udd = b.config.user_data_dir
    print("pid", pid, "udd", udd)
    try:
        tab = await b.get("about:blank")
        if MODE == "attached":
            await tab.evaluate("1")
            print("tab attached session:", tab.session_id is not None)
        os.kill(pid, signal.SIGSTOP)
        print("SIGSTOP sent")
        t = asyncio.create_task(b.stop())
        done, _ = await asyncio.wait({t}, timeout=12)
        if t in done:
            print("stop() returned:", t.exception())
        else:
            print("stop() STILL PENDING after 12s")
            t.print_stack(file=sys.stdout)
            c = t.get_coro()
            print("cr_await chain:")
            while c is not None and hasattr(c, "cr_frame"):
                f = c.cr_frame
                if f is not None:
                    print("   ", f.f_code.co_qualname, f.f_code.co_filename.split("/")[-1] + ":" + str(f.f_lineno))
                c = getattr(c, "cr_await", None)
            print("    awaiting:", repr(c)[:120])
            # process state
            try:
                with open(f"/proc/{pid}/stat") as f:
                    print("proc state:", f.read().split()[2])
            except FileNotFoundError:
                print("process gone")
            print("browser._process still set:", b._process is not None)
            print("profile exists:", os.path.exists(udd))
            t.cancel()
            try:
                await asyncio.wait_for(t, 5)
            except BaseException as e:
                print("after cancel:", type(e).__name__)
            print("after cancelling stop: proc alive:", os.path.exists(f"/proc/{pid}"),
                  "profile exists:", os.path.exists(udd))
            # registry / atexit status
            import asyncio_atexit
            from zendriver.core import util
            print("in registry:", b in util.get_registered_instances())
    finally:
        # cleanup our own process
        try:
            os.kill(pid, signal.SIGCONT)
            os.kill(pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        try:
            os.waitpid(pid, 0)
        except ChildProcessError:
            pass
        import shutil
        shutil.rmtree(udd, ignore_errors=True)
        print("cleaned up; proc alive:", os.path.exists(f"/proc/{pid}"))


asyncio.run(asyncio.wait_for(main(), 60))
