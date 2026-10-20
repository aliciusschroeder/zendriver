import asyncio, pathlib, traceback, time, sys
import zendriver as zd
from zendriver import cdp
SITE = pathlib.Path(__file__).parent / "site"
import http.server, threading, functools
H = functools.partial(http.server.SimpleHTTPRequestHandler, directory=str(SITE))
srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), functools.partial(http.server.SimpleHTTPRequestHandler, directory=str(SITE)))
threading.Thread(target=srv.serve_forever, daemon=True).start()
def url(n): return f"http://127.0.0.1:{srv.server_address[1]}/{n}"
async def step(name, coro, t=30):
    t0 = time.monotonic()
    try:
        r = await asyncio.wait_for(coro, t)
        print(f"[{name}] OK in {time.monotonic()-t0:.2f}s ->", repr(r)[:200]); return r
    except BaseException as e:
        print(f"[{name}] EXC in {time.monotonic()-t0:.2f}s -> {type(e).__name__}: {str(e)[:200]}")
async def main():
    browser = await zd.start(headless=True)
    try:
        tab = await browser.get(url("iframe_src.html"))
        await tab.wait_for_ready_state("complete"); await asyncio.sleep(0.5)
        el = await tab.find_element_by_text("inner needle")
        print("elem:", el.tag, el.node_type)
        await el.click(); await asyncio.sleep(0.3)
        print("clicked in iframe? ->", await tab.evaluate("document.querySelector('iframe').contentWindow.clicked"))
        btn = await tab.find("inner needle", best_match=True)
        await btn.click(); await asyncio.sleep(0.3)
        print("after best_match click ->", await tab.evaluate("document.querySelector('iframe').contentWindow.clicked"))

        t2 = await browser.get(url("simple.html"), new_tab=True)
        print("tabs before:", len(browser.tabs))
        await step("close new tab", t2.close())
        print("tabs after:", len(browser.tabs), "t2 in tabs:", t2 in browser.tabs, "t2.closed:", t2.closed)
        await step("close again", t2.close())
        await step("evaluate after close", t2.evaluate("1+1"), 10)
        t3 = await browser.get(url("simple.html"), new_tab=True)
        await step("close concurrently x2", asyncio.gather(t3.close(), t3.close(), return_exceptions=True))
        print("handlers on browser conn for TargetDestroyed:", len(browser.connection.handlers.get(cdp.target.TargetDestroyed, [])))
    finally:
        await browser.stop()
asyncio.run(main())
