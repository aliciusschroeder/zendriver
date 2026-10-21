import asyncio, os, sys, pathlib, time, subprocess
import zendriver as zd
from zendriver import cdp
print("zendriver from", zd.__file__, "python", sys.version.split()[0])
D = os.path.dirname(os.path.abspath(__file__))
URL = pathlib.Path(D, "r46.html").as_uri()
def descendants(pid):
    out = subprocess.run(["ps", "-e", "-o", "pid=,ppid=,args="], capture_output=True, text=True).stdout
    rows = [l.split(None, 2) for l in out.splitlines() if l.strip()]
    kids = {}; args = {}
    for r in rows:
        p, pp = int(r[0]), int(r[1]); args[p] = r[2] if len(r) > 2 else ""
        kids.setdefault(pp, []).append(p)
    res = []; st = [pid]
    while st:
        p = st.pop()
        for c in kids.get(p, []): res.append(c); st.append(c)
    return [(p, args[p]) for p in res]
def rss_kb(pid):
    with open(f"/proc/{pid}/status") as f:
        for l in f:
            if l.startswith("VmRSS"): return int(l.split()[1])
async def main():
    browser = await zd.start(headless=True)
    try:
        tab = await browser.get(URL); await tab.sleep(0.5)
        rends = [p for p, a in descendants(browser._process_pid) if "--type=renderer" in a and "--extension-process" not in a]
        print("renderer pids", rends)
        inp = await tab.select("#inp")
        await inp.apply("(e)=>1")
        await tab.send(cdp.heap_profiler.collect_garbage())
        N = 30000
        c0 = {p: rss_kb(p) for p in rends}
        for i in range(N):
            ro = await tab.send(cdp.dom.resolve_node(backend_node_id=inp.backend_node_id))
            await tab.send(cdp.runtime.call_function_on("(e)=>1", object_id=ro.object_id, arguments=[cdp.runtime.CallArgument(object_id=ro.object_id)], return_by_value=True))
            await tab.send(cdp.runtime.release_object(ro.object_id))
        await tab.send(cdp.heap_profiler.collect_garbage()); await asyncio.sleep(1)
        c1 = {p: rss_kb(p) for p in rends}
        print(f"[control, released] {N} resolve+call+release; renderer RSS kB before {c0} after {c1}")
        r0 = {p: rss_kb(p) for p in rends}
        t0 = time.monotonic()
        for i in range(N):
            await inp.apply("(e) => 1")
        await tab.send(cdp.heap_profiler.collect_garbage())
        await asyncio.sleep(1)
        r1 = {p: rss_kb(p) for p in rends}
        print(f"[A8.13] {N} apply() in {time.monotonic()-t0:.1f}s; renderer RSS kB before {r0} after {r1}")
        rid = inp._remote_object.object_id
        print("   last object id:", rid)
        # control: release everything by navigating (new context)
    finally:
        await browser.stop(); print("browser stopped")
asyncio.run(asyncio.wait_for(main(), 115))
