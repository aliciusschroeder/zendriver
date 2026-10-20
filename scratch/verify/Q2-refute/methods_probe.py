"""Phase B/C/D: run every member method against real headless Chromium."""
import asyncio
import io
import sys
import time

import zendriver
from zendriver import cdp
from zendriver.core.cloudflare import cf_is_interactive_challenge_present

print("zendriver from", zendriver.__file__, "python", sys.version.split()[0])

PAGE = "data:text/html,<p id='topp'>hello world</p>"


def calls(tab, T):
    return {
        "select(#nope)": lambda: tab.select("#nope", timeout=T),
        "select(#topp) [exists]": lambda: tab.select("#topp", timeout=T),
        "find(nope)": lambda: tab.find("nopenope", timeout=T),
        "find_all(nope)": lambda: tab.find_all("nopenope", timeout=T),
        "select_all(#nope)": lambda: tab.select_all("#nope", timeout=T),
        "select(#nope,frames)": lambda: tab.select("#nope", timeout=T, include_frames=True),
        "xpath(//nope)": lambda: tab.xpath("//nope", timeout=T),
        "wait_for(selector)": lambda: tab.wait_for(selector="#nope", timeout=T),
        "wait_for(text)": lambda: tab.wait_for(text="nopenope", timeout=T),
        "tab(selector=)": lambda: tab(selector="#nope", timeout=T),
        "cf_is_present": lambda: cf_is_interactive_challenge_present(tab, timeout=T),
        "verify_cf": lambda: tab.verify_cf(timeout=T),
    }


def stack_of(task):
    buf = io.StringIO()
    task.print_stack(file=buf, limit=3)
    lines = [l.strip() for l in buf.getvalue().splitlines() if l.strip().startswith("File")]
    return " | ".join(l.split("zendriver/")[-1] for l in lines[:3])


async def run_concurrently(tab, T, wait):
    t0 = time.monotonic()
    tasks = {}
    for name, fn in calls(tab, T).items():
        task = asyncio.ensure_future(fn())
        task._t0 = time.monotonic()
        task.add_done_callback(lambda t: setattr(t, "_t1", time.monotonic()))
        tasks[name] = task
    await asyncio.wait(tasks.values(), timeout=wait)
    for name, task in tasks.items():
        if task.done():
            exc = task.exception()
            res = f"raised {type(exc).__name__}" if exc else f"returned {str(task.result())[:30]!r}"
            print(f"   {name:24s} done after {task._t1 - task._t0:5.2f}s: {res}")
        else:
            print(f"   {name:24s} STILL PENDING after {time.monotonic()-t0:.1f}s (timeout={T}) at {stack_of(task)}")
    return tasks


async def main():
    browser = await zendriver.start(headless=True)
    try:
        tab = browser.main_tab
        await tab.get(PAGE)
        print("B1: no Page.enable/handlers; alert via setTimeout; all methods timeout=2, outer 12s")
        await tab.evaluate("setTimeout(()=>alert('x'),200)")
        await asyncio.sleep(1.0)
        tasks = await run_concurrently(tab, 2, 12)
        print("B2: dismiss dialog; do pending calls now finish?")
        for attempt in ("without Page.enable", "after late Page.enable"):
            if attempt.startswith("after"):
                try:
                    await asyncio.wait_for(tab.send(cdp.page.enable()), 4)
                    print("   late Page.enable answered")
                except Exception as e:
                    print("   late Page.enable:", type(e).__name__, str(e)[:60])
            try:
                await asyncio.wait_for(tab.send(cdp.page.handle_java_script_dialog(True)), 4)
                print(f"   handleJavaScriptDialog {attempt}: OK")
                break
            except Exception as e:
                print(f"   handleJavaScriptDialog {attempt}: {type(e).__name__} {str(e).splitlines()[0][:60]}")
        await asyncio.wait([t for t in tasks.values() if not t.done()], timeout=15)
        for name, task in tasks.items():
            if task.done():
                exc = task.exception()
                res = f"raised {type(exc).__name__}" if exc else "returned"
                print(f"   {name:24s} finished at {task._t1 - task._t0:5.2f}s: {res}")
            else:
                print(f"   {name:24s} still pending")
                task.cancel()

        print("C1: busy main thread for 8s; all methods timeout=2")
        await tab.get(PAGE)
        await tab.evaluate("setTimeout(()=>{const e=Date.now()+8000; while(Date.now()<e){}},100)")
        await asyncio.sleep(0.5)
        tasks = await run_concurrently(tab, 2, 25)
        for t in tasks.values():
            if not t.done():
                t.cancel()

        print("D1: xpath timeout semantics on an existing element")
        await tab.get(PAGE)
        for T in (2.5, 0.5, 0.001, 0, -1):
            t0 = time.monotonic()
            r = await asyncio.wait_for(tab.xpath("//p[@id='topp']", timeout=T), 10)
            print(f"   xpath(//p[@id=topp], timeout={T}) -> {len(r)} items in {time.monotonic()-t0:.3f}s")
        for name, fn in (("find('hello', timeout=0)", lambda: tab.find("hello", timeout=0)),
                         ("select('#topp', timeout=0)", lambda: tab.select("#topp", timeout=0))):
            r = await asyncio.wait_for(fn(), 10)
            print(f"   {name} -> {str(r)[:40]}")
        print("D2: send count during a 0.5s xpath miss")
        n = 0
        orig = tab.send

        async def counting_send(*a, **k):
            nonlocal n
            n += 1
            return await orig(*a, **k)

        tab.send = counting_send
        t0 = time.monotonic()
        r = await asyncio.wait_for(tab.xpath("//nope", timeout=0.5), 10)
        el = time.monotonic() - t0
        tab.send = orig
        print(f"   xpath miss -> {r} in {el:.2f}s, Tab.send calls: {n}")
        n = 0
        tab.send = counting_send
        try:
            await asyncio.wait_for(tab.select("#nope", timeout=0.5), 10)
        except asyncio.TimeoutError:
            pass
        tab.send = orig
        print(f"   for comparison select miss timeout=0.5, Tab.send calls: {n}")
    finally:
        await browser.stop()


asyncio.run(main())
