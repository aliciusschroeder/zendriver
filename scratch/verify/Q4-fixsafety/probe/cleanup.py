import json, os, signal, sys, shutil, time
dirs, pids = set(), set()
for fn in sys.argv[1:]:
    for line in open(fn):
        line=line.strip()
        if not line: continue
        d = json.loads(line)
        if isinstance(d, dict):
            dirs.update(d.get("dirs", [])); pids.update(d.get("pids", []))
me = os.getpid()
victims = set()
for pid in os.listdir("/proc"):
    if not pid.isdigit() or int(pid) == me: continue
    try:
        args = open(f"/proc/{pid}/cmdline","rb").read().split(b"\0")
    except OSError: continue
    args = [a.decode(errors="replace") for a in args]
    if any(a in {f"--user-data-dir={d}" for d in dirs} for a in args):
        victims.add(int(pid))
print("killing", sorted(victims))
for v in victims:
    try: os.kill(v, signal.SIGKILL)
    except ProcessLookupError: pass
time.sleep(1)
for d in dirs:
    if os.path.exists(d):
        shutil.rmtree(d, ignore_errors=True); print("removed", d)
