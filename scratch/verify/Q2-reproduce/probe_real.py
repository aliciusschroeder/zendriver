"""Q2 reproducer: polling methods with a timeout vs. a blocked renderer.

usage: probe_real.py MODE [case ...]
MODE: alert | busy | busy12 (12s busy loop, measures overshoot)
"""
import asyncio
import io
import os
import signal
import sys
import time

import zendriver
from zendriver.core import cloudflare

print("zendriver imported from", zendriver.__file__, "python", sys.version.split()[0], flush=True)

MODE = sys.argv[1]
ONLY = sys.argv[2:]
OUTER = float(os.environ.get("OUTER", "8"))

PAGE = "data:text/html,<html><body><p id=topp>hello world</p></body></html>"

if MODE == "alert":
    TRIGGER = "setTimeout(()=>alert('blocking'),200)"
elif MODE == "busy":
    TRIGGER = "setTimeout(()=>{while(true){}},200)"
elif MODE == "busy12":
    TRIGGER = "setTimeout(()=>{const e=Date.now()+12000; while(Date.now()<e){}},200)"
else:
    raise SystemExit("bad mode")

CASES = {
    "select": lambda t: t.select("#nope", timeout=2),
    "select_frames": lambda t: t.select("#nope", timeout=2, include_frames=True),
    "find": lambda t: t.find("zz-nope-text", timeout=2),
    "find_all": lambda t: t.find_all("zz-nope-text", timeout=2),
    "select_all": lambda t: t.select_all("#nope", timeout=2),
    "xpath": lambda t: t.xpath("//nope", timeout=2),
    "wait_for_sel": lambda t: t.wait_for(selector="#nope", timeout=2),
    "wait_for_text": lambda t: t.wait_for(text="zz-nope-text", timeout=2),
    "call_sel": lambda t: t(selector="#nope", timeout=2),
    "cf_present": lambda t: cloudflare.cf_is_interactive_challenge_present(t, timeout=2),
    "verify_cf": lambda t: t.verify_cf(timeout=2),
    # controls
    "CTRL_wait_for_ready_state": lambda t: t.wait_for_ready_state("complete", timeout=2),
    "CTRL_wait": lambda t: t.wait(2),
}


def stack_of(task):
    buf = io.StringIO()
    task.print_stack(file=buf)
    lines = [l for l in buf.getvalue().splitlines() if l.strip()]
    return "\n      ".join(lines[-8:])


async def run_case(browser, name, fn):
    tab = await browser.get(PAGE, new_tab=True)
    await tab.wait_for_ready_state("complete", timeout=5)
    await tab.evaluate(TRIGGER)
    await asyncio.sleep(1.0)
    t0 = time.monotonic()
    task = asyncio.ensure_future(fn(tab))
    done, _ = await asyncio.wait({task}, timeout=OUTER)
    el = time.monotonic() - t0
    if task in done:
        exc = task.exception()
        if exc is not None:
            res = f"raised {type(exc).__name__}: {exc}"
        else:
            res = f"returned {task.result()!r}"
        print(f"[{MODE}] {name}: DONE in {el:.2f}s -> {res}", flush=True)
    else:
        print(f"[{MODE}] {name}: STILL PENDING after {el:.2f}s (timeout=2); stack:\n      {stack_of(task)}", flush=True)
        task.cancel()
        try:
            await asyncio.wait_for(asyncio.shield(asyncio.gather(task, return_exceptions=True)), 3)
        except Exception:
            pass
    # close the blocked tab from the browser connection
    try:
        await asyncio.wait_for(
            browser.connection.send(zendriver.cdp.target.close_target(tab.target_id)), 5
        )
    except Exception as e:
        print("   close_target failed:", type(e).__name__, e)


async def main():
    browser = await zendriver.start(headless=True)
    pid = browser._process_pid
    print("chromium pid", pid, flush=True)
    try:
        for name, fn in CASES.items():
            if ONLY and name not in ONLY:
                continue
            await run_case(browser, name, fn)
    finally:
        try:
            await asyncio.wait_for(browser.stop(), 20)
        except Exception as e:
            print("stop failed", e)
            try:
                os.kill(pid, signal.SIGKILL)
            except Exception:
                pass


asyncio.run(main())
