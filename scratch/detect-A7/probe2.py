import asyncio, sys, threading, http.server, functools, os, glob, shutil
import zendriver as zd
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, "site")
WORK = os.path.join(HERE, "work2")

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
        # A: tab A sets path, tab B download_file -> where?
        tab_a = await browser.get(base + "/dl.html")
        await tab_a.set_download_path(os.path.join(WORK, "dirA"))
        tab_b = await browser.get(base + "/dl.html", new_tab=True)
        import warnings
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            await tab_b.download_file(base + "/docs/data.txt", "b.txt")
            print("warnings:", [str(x.message) for x in w])
        await asyncio.sleep(2)
        print("after tab_b.download_file:", listing())
        # now tab A clicks its link: expected dirA
        await (await tab_a.select("#dl")).click()
        await asyncio.sleep(2)
        print("after tab_a link click (tab_a set dirA):", listing())

        # B: quote in filename
        await tab_a.download_file(base + "/docs/data.txt", "O'Reilly.txt")
        await asyncio.sleep(2)
        print("after download_file(\"O'Reilly.txt\"):", listing())

        # C: context tab
        ctx_tab = await browser.create_context(base + "/dl.html", )
        await ctx_tab.wait_for_ready_state("complete")
        await ctx_tab.set_download_path(os.path.join(WORK, "dirCtx"))
        await (await ctx_tab.select("#dl")).click()
        await asyncio.sleep(3)
        print("after ctx_tab link click (ctx_tab set dirCtx):", listing())
        # D: expect_download on context tab
        try:
            async with ctx_tab.expect_download() as ex:
                await (await ctx_tab.select("#dl")).click()
                d = await asyncio.wait_for(ex.value, 5)
                print("ctx expect_download got", d.suggested_filename)
        except asyncio.TimeoutError:
            print("ctx expect_download: TIMEOUT, no DownloadWillBegin")
        await asyncio.sleep(2)
        print("after ctx expect_download (should be denied):", listing())
    finally:
        await browser.stop()
        srv.shutdown()

asyncio.run(asyncio.wait_for(main(), 100))
