import asyncio, os, sys, time, logging, subprocess
import psutil
import zendriver as zd
from zendriver.core import util
CHROME = os.popen("which chromium").read().strip()
headless = sys.argv[1] == "headless"
async def main():
    b = await zd.start(headless=headless, sandbox=False, browser_executable_path=CHROME)
    await b.get("data:text/html,<p>hi</p>")
    p = psutil.Process(b._process_pid)
    pid = b._process_pid
    tail = util._stderr_tails.get(b._process)
    for c in [p] + p.children(recursive=True):
        try:
            fd2 = os.readlink(f"/proc/{c.pid}/fd/2")
        except OSError as e:
            fd2 = repr(e)
        print(c.pid, c.ppid(), c.name(), " ".join(c.cmdline()[1:2])[:60], "fd2=", fd2)
    # crashpad handlers anywhere
    for q in psutil.process_iter(["name", "cmdline"]):
        if "crashpad" in (q.info["name"] or ""):
            print("crashpad:", q.pid, q.ppid())
    # simulate a browser that ignores SIGTERM: SIGKILL only the main process
    if len(sys.argv) > 2 and sys.argv[2] == "sigkill_main":
        os.kill(pid, 9)
        await asyncio.sleep(1)
        print("after SIGKILL of main: thread alive", tail._thread.is_alive(), "children alive", [c.pid for c in p.children(recursive=True)])
        for c in psutil.process_iter(["ppid", "name"]):
            pass
    await b.stop()
    await asyncio.sleep(0.5)
    print("after stop: thread alive", tail._thread.is_alive())
asyncio.run(main())
