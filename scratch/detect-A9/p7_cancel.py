import asyncio, os, glob, tempfile, time, sys
import psutil
import zendriver as zd

def chromes():
    out = []
    for p in psutil.process_iter(["pid", "name", "cmdline", "ppid"]):
        try:
            cl = p.info["cmdline"] or []
            if cl and "chrome" in os.path.basename(cl[0]) and any(a.startswith("--remote-debugging-port") for a in cl):
                out.append((p.pid, [a for a in cl if a.startswith("--user-data-dir")][0]))
        except Exception: pass
    return out

async def main(t):
    before = set(chromes())
    try:
        await asyncio.wait_for(zd.start(headless=True), t)
        print("started (no timeout)")
    except asyncio.TimeoutError:
        print(f"zd.start timed out after {t}s")
    await asyncio.sleep(2)
    leaked = set(chromes()) - before
    print("registered instances:", len(zd.util.get_registered_instances()))
    print("chrome browser processes still alive:", leaked)
    return leaked

leaked = asyncio.run(main(float(sys.argv[1])))
time.sleep(1)
for pid, udd in leaked:
    print("after asyncio.run exit, pid", pid, "alive:", psutil.pid_exists(pid), "profile exists:", os.path.exists(udd.split("=",1)[1]))
    try: psutil.Process(pid).kill()
    except Exception: pass
