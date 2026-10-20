import asyncio, sys, time
import zendriver as zd

MODE = sys.argv[1]  # busy | alert
METHOD = sys.argv[2]

async def main():
    browser = await zd.start(headless=True)
    try:
        tab = browser.main_tab
        await tab.get("data:text/html,<html><body><p>hello</p></body></html>")
        await tab.wait_for_ready_state("complete", timeout=5)
        if MODE == "busy":
            await tab.evaluate("setTimeout(() => { while (true) {} }, 200)")
        else:
            await tab.evaluate("setTimeout(() => { alert('x') }, 200)")
        await asyncio.sleep(1)
        coro = {
            "select": lambda: tab.select("#nope", timeout=2),
            "find": lambda: tab.find("nope-text", timeout=2),
            "find_all": lambda: tab.find_all("nope-text", timeout=2),
            "select_all": lambda: tab.select_all("#nope", timeout=2),
            "wait_for": lambda: tab.wait_for(selector="#nope", timeout=2),
            "call": lambda: tab(selector="#nope", timeout=2),
            "xpath": lambda: tab.xpath("//nope", timeout=2),
            "ready": lambda: tab.wait_for_ready_state("complete", timeout=2),
            "wait": lambda: tab.wait(2),
            "sleep": lambda: tab.sleep(0.5),
            "cf": lambda: __import__("zendriver.core.cloudflare", fromlist=["x"]).cf_is_interactive_challenge_present(tab, timeout=2),
            "verify_cf": lambda: tab.verify_cf(timeout=2),
        }[METHOD]
        t0 = time.monotonic()
        task = asyncio.ensure_future(coro())
        done, _ = await asyncio.wait({task}, timeout=15)
        dt = time.monotonic() - t0
        if task in done:
            exc = task.exception()
            print(f"{MODE} {METHOD}: finished after {dt:.1f}s -> {type(exc).__name__ if exc else 'ok'}: {exc if exc else task.result()}")
        else:
            print(f"{MODE} {METHOD}: STILL PENDING after {dt:.1f}s (timeout=2)")
            task.print_stack(limit=30)
            task.cancel()
    finally:
        try:
            await asyncio.wait_for(browser.stop(), 15)
        except Exception as e:
            print("stop failed", type(e).__name__, e)
            if browser._process: browser._process.kill()

asyncio.run(main())
