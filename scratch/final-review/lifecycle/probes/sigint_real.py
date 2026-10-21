"""SIGINT the python process (a) while sleeping with a running browser and no stop()
(b) during zd.start(). prints pid/profile for the parent to check afterwards."""
import asyncio, os, shutil, signal, sys, threading, time, logging
import zendriver as zd
from zendriver.core import util
logging.basicConfig(level=logging.WARNING, format="LOG %(levelname)s %(name)s: %(message)s")
CHROME = shutil.which("chromium")
when = sys.argv[1]
real = util._start_process
def track(*a, **k):
    p = real(*a, **k)
    print("PID", p.pid, flush=True)
    print("UDD", [x for x in a[1] if x.startswith("--user-data-dir=")][0].split("=",1)[1], flush=True)
    return p
util._start_process = track

def sigint_later(d):
    time.sleep(d); os.kill(os.getpid(), signal.SIGINT)

async def main():
    if when == "during_start":
        threading.Thread(target=sigint_later, args=(float(sys.argv[2]),), daemon=True).start()
    b = await zd.start(headless=True, sandbox=False, browser_executable_path=CHROME)
    print("PROFILE", b.config.user_data_dir, flush=True)
    if when == "during_sleep":
        threading.Thread(target=sigint_later, args=(0.5,), daemon=True).start()
        await asyncio.sleep(30)
    else:
        await b.stop()
try:
    asyncio.run(main())
except KeyboardInterrupt:
    print("KeyboardInterrupt", flush=True)
