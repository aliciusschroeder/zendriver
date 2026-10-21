import asyncio, os, sys, time, threading, logging
import psutil
import zendriver as zd
from zendriver.core import util

mode = sys.argv[1] if len(sys.argv) > 1 else "never"
logging.basicConfig(level=logging.WARNING, format="LOG %(levelname)s %(name)s: %(message)s")
info = {}

async def main():
    b = await zd.start(headless=True, sandbox=False, browser_executable_path=os.popen("which chromium").read().strip())
    tab = await b.get("about:blank")
    await tab.evaluate("1+1")
    p = psutil.Process(b._process_pid)
    info["pid"] = b._process_pid
    info["children"] = [c.pid for c in p.children(recursive=True)]
    info["profile"] = b.config.user_data_dir
    info["stderr_fd"] = b._process.stderr.fileno()
    info["tail"] = util._stderr_tails.get(b._process)
    info["t_main_end"] = time.monotonic()
    if mode == "cancelled_stop":
        try:
            await asyncio.wait_for(b.stop(), 0.01)
        except asyncio.TimeoutError:
            print("stop timed out")
    print("main done", flush=True)

asyncio.run(main())
t = time.monotonic() - info["t_main_end"]
print("asyncio.run close took %.2fs" % t)
alive = [pid for pid in [info["pid"]] + info["children"] if psutil.pid_exists(pid) and psutil.Process(pid).status() != psutil.STATUS_ZOMBIE]
print("alive chrome pids:", alive)
print("profile exists:", os.path.exists(info["profile"]))
tail = info["tail"]
print("drain thread alive:", tail._thread.is_alive() if tail else None)
try:
    os.fstat(info["stderr_fd"]); print("stderr fd still open (fd %d) -> %s" % (info["stderr_fd"], os.readlink("/proc/self/fd/%d" % info["stderr_fd"])))
except OSError:
    print("stderr fd closed")
print("threads:", [th.name for th in threading.enumerate()])
