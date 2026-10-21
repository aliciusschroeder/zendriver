"""public-API flow: Page enabled (to be able to dismiss dialogs), page opens an
alert, user starts tab.expect_request() (adds Network handlers, enable is lazy),
a bounded tab.select() times out, then the user dismisses the dialog."""
import asyncio, logging, os, sys, time
import zendriver as zd
from zendriver import cdp

logging.basicConfig(level=logging.WARNING)


async def step(label, coro, net):
    t0 = time.monotonic()
    try:
        r = await asyncio.wait_for(coro, net)
        print(f"  {label}: OK {r!r:.50} after {time.monotonic()-t0:.2f}s", flush=True)
    except BaseException as e:
        print(f"  {label}: {type(e).__name__} {str(e)[:60]!r} after {time.monotonic()-t0:.2f}s", flush=True)


async def main():
    print("python", sys.version.split()[0], zd.__file__, flush=True)
    browser = await zd.start(headless=True, sandbox=False, browser_executable_path=os.environ["CHROME"])
    print("chrome pid", browser._process_pid, flush=True)
    try:
        tab = browser.main_tab
        await tab.get("data:text/html,<p id=hello>hello</p>")
        await tab.send(cdp.page.enable())
        await tab.evaluate("setTimeout(() => alert('blocked'), 50)")
        await asyncio.sleep(0.5)
        async with tab.expect_request(".*") as req:
            await step("tab.select('#nope', timeout=1)", tab.select("#nope", timeout=1), 10)
            await step("tab.send(Page.handleJavaScriptDialog)", tab.send(cdp.page.handle_java_script_dialog(accept=True)), 8)
            await step("tab.select('#hello', timeout=2)", tab.select("#hello", timeout=2), 8)
    finally:
        await asyncio.wait_for(browser.stop(), 60)
        print("  stopped, process gone:", browser._process is None, flush=True)

asyncio.run(main())
