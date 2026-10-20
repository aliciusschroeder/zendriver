import asyncio, threading, http.server, functools, os, glob, shutil
import zendriver as zd
from zendriver import cdp
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, "site")
WORK = os.path.join(HERE, "work3")

def serve():
    class H(http.server.SimpleHTTPRequestHandler):
        def log_message(self, *a): pass
    srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), functools.partial(H, directory=ROOT))
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv

def listing():
    return sorted(os.path.relpath(p, WORK) for p in glob.glob(WORK + "/**/*", recursive=True) if os.path.isfile(p))

async def main():
    shutil.rmtree(WORK, ignore_errors=True); os.makedirs(WORK)
    os.chdir(WORK)
    srv = serve()
    base = f"http://127.0.0.1:{srv.server_address[1]}"
    browser = await zd.start(headless=True)
    try:
        ctx_tab = await browser.create_context(base + "/dl.html")
        await ctx_tab.wait_for_ready_state("complete")
        await ctx_tab.set_download_path(os.path.join(WORK, "dirCtx"))
        await (await ctx_tab.select("#dl")).click()
        await asyncio.sleep(3)
        print("1 set_download_path on ctx tab, click:", listing())
        ctx_id = ctx_tab.target.browser_context_id
        await ctx_tab.send(cdp.browser.set_download_behavior(behavior="allow", download_path=os.path.join(WORK, "dirCtxExplicit"), browser_context_id=ctx_id))
        await (await ctx_tab.select("#dl")).click()
        await asyncio.sleep(3)
        print("2 with browser_context_id, click:", listing())
        # expect_download control
        got = asyncio.get_running_loop().create_future()
        async def h(ev):
            if not got.done(): got.set_result(ev)
        await ctx_tab.send(cdp.browser.set_download_behavior(behavior="deny", events_enabled=True, browser_context_id=ctx_id))
        ctx_tab.add_handler(cdp.browser.DownloadWillBegin, h)
        await (await ctx_tab.select("#dl")).click()
        try:
            ev = await asyncio.wait_for(got, 5)
            print("3 DownloadWillBegin with browser_context_id:", ev.suggested_filename)
        except asyncio.TimeoutError:
            print("3 no event even with context id")
    finally:
        await browser.stop()
        srv.shutdown()

asyncio.run(asyncio.wait_for(main(), 100))
