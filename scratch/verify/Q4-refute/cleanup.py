import json, sys, shutil, os, psutil
for f in sys.argv[1:]:
    for s in json.load(open(f)):
        try:
            p = psutil.Process(s["pid"])
            procs = [p] + p.children(recursive=True)
            for c in procs:
                try: c.kill()
                except psutil.NoSuchProcess: pass
            psutil.wait_procs(procs, timeout=5)
            print("killed", [c.pid for c in procs])
        except psutil.NoSuchProcess:
            pass
        if s.get("udd") and os.path.exists(s["udd"]):
            shutil.rmtree(s["udd"], ignore_errors=True); print("removed", s["udd"])
