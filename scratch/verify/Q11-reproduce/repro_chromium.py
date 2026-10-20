import asyncio, os, sys, time, tempfile, shutil
import zendriver
print("zendriver from:", zendriver.__file__, "python", sys.version.split()[0])

async def trial(tab, label, until, timeout):
    t0 = time.monotonic()
    try:
        r = await asyncio.wait_for(tab.wait_for_ready_state(until, timeout=timeout) if until else tab.wait_for_ready_state(timeout=timeout), timeout + 10)
        print(f"[{label}] returned {r!r} in {time.monotonic()-t0:.2f}s")
    except BaseException as e:
        print(f"[{label}] EXC in {time.monotonic()-t0:.2f}s -> {type(e).__name__}: {e}")

async def main():
    d = tempfile.mkdtemp(dir=os.getcwd(), prefix="page_")
    p = os.path.join(d, "fast.html")
    open(p, "w").write("<html><body><h1>hi</h1></body></html>")
    url = "file://" + p
    browser = await zendriver.start(headless=True)
    try:
        tab = await browser.get(url)
        await asyncio.sleep(1)
        rs = await tab.evaluate("document.readyState")
        print("readyState after 1s:", rs)
        await trial(tab, "default (interactive) on complete page", None, 3)
        await trial(tab, "until='interactive' on complete page", "interactive", 3)
        await trial(tab, "until='loading' on complete page", "loading", 2)
        await trial(tab, "until='complete' on complete page (control)", "complete", 3)
        # realistic flow: get then default wait, no sleep
        tab2 = await browser.get(url, new_tab=True)
        rs2 = await tab2.evaluate("document.readyState")
        print("readyState immediately after get (new tab):", rs2)
        await trial(tab2, "get() then default wait, no sleep", None, 3)
        print("readyState at end:", await tab2.evaluate("document.readyState"))
    finally:
        await browser.stop()
        shutil.rmtree(d, ignore_errors=True)

asyncio.run(main())
