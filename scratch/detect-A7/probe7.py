import asyncio, threading, http.server, functools, os, glob, shutil, warnings
import zendriver as zd
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, "site")
WORK = os.path.join(HERE, "work7")
warnings.simplefilter("ignore")
def serve():
    class H(http.server.SimpleHTTPRequestHandler):
        def log_message(self, *a): pass
    srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), functools.partial(H, directory=ROOT))
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv
def listing():
    return sorted(os.path.relpath(p, WORK) for p in glob.glob(WORK + "/**/*", recursive=True) if os.path.isfile(p))
async def main():
    shutil.rmtree(WORK, ignore_errors=True); os.makedirs(WORK); os.chdir(WORK)
    srv = serve()
    base = f"http://127.0.0.1:{srv.server_address[1]}"
    browser = await zd.start(headless=True)
    try:
        tab = await browser.get(base + "/dl.html")
        await tab.wait_for_ready_state("complete")
        # control: link click inside expect_download
        async with tab.expect_download() as ex:
            await (await tab.select("#dl")).click()
            d = await asyncio.wait_for(ex.value, 5)
            print("control: link click ->", d.suggested_filename)
        # download_file inside expect_download, no download path set on this tab
        tab2 = await browser.get(base + "/dl.html", new_tab=True)
        await tab2.wait_for_ready_state("complete")
        try:
            async with tab2.expect_download() as ex:
                await tab2.download_file(base + "/docs/data.txt", "x.txt")
                d = await asyncio.wait_for(ex.value, 5)
                print("download_file in expect_download ->", d.suggested_filename)
        except asyncio.TimeoutError:
            print("download_file in expect_download: DownloadWillBegin never delivered (would hang without wait_for)")
        await asyncio.sleep(1)
        print("files:", listing())
        # after a set_download_path, expect_download then link click
        try:
            async with tab2.expect_download() as ex:
                await tab2.set_download_path(os.path.join(WORK, "p"))
                await (await tab2.select("#dl")).click()
                d = await asyncio.wait_for(ex.value, 5)
                print("set_download_path in expect_download ->", d.suggested_filename)
        except asyncio.TimeoutError:
            print("set_download_path inside expect_download: no event")
    finally:
        await browser.stop(); srv.shutdown()
asyncio.run(asyncio.wait_for(main(), 100))
