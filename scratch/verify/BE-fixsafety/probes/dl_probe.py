import asyncio, os, pathlib, shutil, tempfile, threading, functools, http.server, warnings
import zendriver
from zendriver import cdp
print("zendriver from", zendriver.__file__)
warnings.simplefilter("ignore")

def serve(root):
    h = functools.partial(http.server.SimpleHTTPRequestHandler, directory=root)
    h.log_message = lambda *a: None
    srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), h)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv

def ls(d):
    d = pathlib.Path(d)
    return sorted(str(p.relative_to(d)) for p in d.rglob("*") if p.is_file()) if d.exists() else []

async def click_dl(tab, name):
    await tab.evaluate(f"(()=>{{const a=document.createElement('a');a.href='/data.txt';a.download='{name}';document.body.appendChild(a);a.click();}})()")

async def wait_file(root, name, t=3):
    for _ in range(int(t*10)):
        if any(f.endswith(name) for f in ls(root)): return True
        await asyncio.sleep(0.1)
    return False

async def main():
    www = tempfile.mkdtemp(); work = tempfile.mkdtemp(); home = os.environ["HOME"]
    (pathlib.Path(www)/"index.html").write_text("<html><body>x</body></html>")
    (pathlib.Path(www)/"data.txt").write_text("hello\n")
    os.chdir(work)
    srv = serve(www); base = f"http://127.0.0.1:{srv.server_port}"
    browser = await zendriver.start(headless=True)
    try:
        # A7.3
        tab = await browser.get(base + "/index.html")
        async with tab.expect_download() as ex:
            await tab.download_file(base + "/data.txt", "x.txt")
            try:
                ev = await asyncio.wait_for(ex.value, 4); print("A7.3 event:", ev.suggested_filename)
            except asyncio.TimeoutError:
                print("A7.3 TIMEOUT: no DownloadWillBegin")
        await asyncio.sleep(1)
        print("A7.3 files in work (expected none, deny):", ls(work))
        # A7.4
        dirA = pathlib.Path(work)/"dirA"
        tab_a = tab
        await tab_a.set_download_path(dirA)
        tab_b = await browser.get(base + "/index.html", new_tab=True)
        await tab_b.download_file(base + "/data.txt", "b.txt")
        await wait_file(work, "b.txt")
        await click_dl(tab_a, "fromA.txt")
        await wait_file(work, "fromA.txt")
        print("A7.4 files:", ls(work))
        # A10.6
        dirB = pathlib.Path(work)/"dirB"
        await tab_b.set_download_path(dirB)
        await tab_b.download_file(base + "/data.txt", "first.txt"); await wait_file(work, "first.txt")
        tab_c = await browser.get(base + "/index.html", new_tab=True)
        async with tab_c.expect_download():
            pass
        print("A10.6 tab_b._download_behavior:", tab_b._download_behavior)
        await tab_b.download_file(base + "/data.txt", "second.txt")
        got = await wait_file(work, "second.txt")
        print("A10.6 files in work:", ls(work), "second in work:", got, "in HOME/Downloads:", ls(pathlib.Path(home)/"Downloads"))
        # A7.2 contexts
        ctx_tab = await browser.create_context(base + "/index.html")
        await ctx_tab.wait_for_ready_state("complete")
        print("ctx id:", ctx_tab.target.browser_context_id, "default tab ctx id:", tab_a.target.browser_context_id)
        dirCtx = pathlib.Path(work)/"dirCtx"
        await ctx_tab.set_download_path(dirCtx)
        await click_dl(ctx_tab, "ctx1.txt")
        got = await wait_file(work, "ctx1.txt")
        print("A7.2 after ctx set_download_path, click: saved:", got, ls(work))
        async with ctx_tab.expect_download() as ex:
            await click_dl(ctx_tab, "ctx2.txt")
            try:
                ev = await asyncio.wait_for(ex.value, 3); print("A7.2 ctx expect_download event:", ev.suggested_filename)
            except asyncio.TimeoutError:
                print("A7.2 ctx expect_download TIMEOUT")
        dirCtx2 = pathlib.Path(work)/"dirCtx2"; dirCtx2.mkdir()
        await ctx_tab.send(cdp.browser.set_download_behavior("allow", browser_context_id=ctx_tab.target.browser_context_id, download_path=str(dirCtx2), events_enabled=True))
        await click_dl(ctx_tab, "ctx3.txt")
        print("A7.2 with explicit browser_context_id saved:", await wait_file(work, "ctx3.txt"), ls(dirCtx2))
        # default context id explicit
        dirDef = pathlib.Path(work)/"dirDef"; dirDef.mkdir()
        try:
            await tab_a.send(cdp.browser.set_download_behavior("allow", browser_context_id=tab_a.target.browser_context_id, download_path=str(dirDef), events_enabled=True))
            await click_dl(tab_a, "def.txt")
            print("default ctx explicit id saved:", await wait_file(work, "def.txt"), ls(dirDef))
        except Exception as e:
            print("default ctx explicit id EXC:", str(e).splitlines()[0])
    finally:
        await browser.stop(); srv.shutdown(); os.chdir("/tmp")
        shutil.rmtree(www, ignore_errors=True); shutil.rmtree(work, ignore_errors=True)

asyncio.run(asyncio.wait_for(main(), 100))
