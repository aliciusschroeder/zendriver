import asyncio, sys, logging, os, json
import zendriver as zd
from zendriver import cdp
print(sys.version.split()[0], zd.__file__)
logging.basicConfig(level=logging.WARNING, format="%(levelname)s %(name)s: %(message)s")

async def main():
    browser = await zd.start(headless=True, sandbox=False, browser_executable_path=os.path.join(os.environ["ZBIN"], "chromium"))
    try:
        tab = await browser.get("about:blank")
        # raw websocket probe of chrome's own limit, via a fresh tab command
        for n in (100, 200, 300, 400, 600, 900, 1200):
            expr = f"(() => {{ let o = {{}}; let c = o; for (let i=0;i<{n};i++) {{ c.a = {{}}; c = c.a; }} return o; }})()"
            try:
                r = await asyncio.wait_for(tab.send(cdp.runtime.evaluate(expr, return_by_value=True)), 10)
                print("evaluate nesting", n, "->", "ok" if r[1] is None else ("exception", r[1].text))
            except Exception as e:
                print("evaluate nesting", n, "-> raised", type(e).__name__, str(e)[:100].replace("\n"," "))
        for n in (100, 150, 200, 250, 300, 400, 500):
            await tab.evaluate(f"""(() => {{ document.body.innerHTML=''; let d = document.body; for (let i=0;i<{n};i++) {{ const x=document.createElement('div'); d.appendChild(x); d=x; }} return 1; }})()""")
            try:
                r = await asyncio.wait_for(tab.send(cdp.dom.get_document(-1, True)), 10)
                print("dom depth", n, "-> ok")
            except Exception as e:
                print("dom depth", n, "-> raised", type(e).__name__, str(e)[:100].replace("\n"," "))
    finally:
        await asyncio.wait_for(browser.stop(), 60)
asyncio.run(main())
