"""3 browsers, never stopped, one frozen (SIGSTOP) if argv[1]=='frozen'. after asyncio.run:
all processes gone? all profiles removed? how long did loop close take?"""
import asyncio, os, shutil, signal, sys, time, logging
import psutil
import zendriver as zd
logging.basicConfig(level=logging.WARNING, format="LOG %(levelname)s %(name)s: %(message)s")
CHROME = shutil.which("chromium")
info = {}
async def main():
    bs = await asyncio.gather(*(zd.start(headless=True, sandbox=False, browser_executable_path=CHROME) for _ in range(3)))
    for b in bs:
        t = await b.get("data:text/html,<p>x</p>")
    info["pids"] = [b._process_pid for b in bs]
    info["all"] = [p for b in bs for p in [b._process_pid] + [c.pid for c in psutil.Process(b._process_pid).children(recursive=True)]]
    info["udd"] = [b.config.user_data_dir for b in bs]
    if len(sys.argv) > 1 and sys.argv[1] == "frozen":
        os.kill(bs[1]._process_pid, signal.SIGSTOP)
    info["t"] = time.monotonic()
print(sys.version.split()[0], zd.__file__)
asyncio.run(main())
print("loop close took %.1fs" % (time.monotonic() - info["t"]))
time.sleep(0.5)
alive = [p for p in info["all"] if psutil.pid_exists(p) and psutil.Process(p).status() != psutil.STATUS_ZOMBIE]
print("alive:", alive, "profiles left:", [u for u in info["udd"] if os.path.exists(u)])
for p in alive:
    try: os.kill(p, signal.SIGKILL)
    except OSError: pass
for u in info["udd"]: shutil.rmtree(u, ignore_errors=True)
