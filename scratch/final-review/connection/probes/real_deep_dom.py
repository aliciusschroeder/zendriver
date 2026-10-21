"""Real trigger for Q1's receive-error path: a page with a deeply nested DOM makes
DOM.getDocument(depth=-1) return JSON nested deeper than json.loads can parse
(RecursionError, an Exception). What do select()/get_content() and concurrent
tab commands see?"""
import asyncio, sys, logging, os, time
import zendriver as zd
from zendriver import cdp

print(sys.version.split()[0], zd.__file__)
logging.basicConfig(level=logging.WARNING, format="%(levelname)s %(name)s: %(message)s")
DEPTH = int(sys.argv[1]) if len(sys.argv) > 1 else 3000

async def main():
    browser = await zd.start(headless=True, sandbox=False, browser_executable_path=os.path.join(os.environ["ZBIN"], "chromium"))
    try:
        tab = await browser.get("about:blank")
        await tab.evaluate(f"""(() => {{ let d = document.body; for (let i=0;i<{DEPTH};i++) {{ const n=document.createElement('div'); d.appendChild(n); d=n; }} d.textContent='deep-leaf'; return 1; }})()""")
        t0 = time.monotonic()
        try:
            r = await asyncio.wait_for(tab.send(cdp.dom.get_document(-1, True)), 20)
            print("getDocument returned node", r.node_name)
        except Exception as e:
            print(f"getDocument raised after {time.monotonic()-t0:.2f}s:", type(e).__name__, str(e)[:120])
        print("browser listener running:", browser.connection.listener.running)
        t0 = time.monotonic()
        try:
            el = await asyncio.wait_for(tab.select("div", timeout=3), 20)
            print("select returned", el)
        except Exception as e:
            print(f"select raised after {time.monotonic()-t0:.2f}s:", type(e).__name__, str(e)[:120])
        print("tab still usable:", await asyncio.wait_for(tab.evaluate("1+1"), 5))
    finally:
        await asyncio.wait_for(browser.stop(), 60)

asyncio.run(main())
