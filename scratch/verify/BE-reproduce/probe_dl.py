import asyncio, os, sys, pathlib, shutil, warnings
import zendriver
from zendriver import cdp
from common import serve
print("zendriver:", zendriver.__file__, "python", sys.version.split()[0])
WORK = pathlib.Path(__file__).parent / "work_dl"
shutil.rmtree(WORK, ignore_errors=True); WORK.mkdir()
HOME = WORK / "home"; HOME.mkdir()
os.environ["HOME"] = str(HOME)   # so Chrome's default ~/Downloads lands in scratch
os.chdir(WORK)
warnings.simplefilter("ignore")

def listing():
    out = {}
    for d in WORK.rglob("*"):
        if d.is_file() and d.suffix in (".txt",) :
            out.setdefault(str(d.parent.relative_to(WORK)), []).append(d.name)
    return {k: sorted(v) for k, v in sorted(out.items())}

async def click_dl(tab):
    await tab.evaluate("document.getElementById('dl').click()")

async def wait_value(ex, label, secs=5):
    t = asyncio.ensure_future(ex.value)
    done, _ = await asyncio.wait({t}, timeout=secs)
    if done:
        print(f"{label}: DownloadWillBegin received: {t.result().suggested_filename}")
        return
    print(f"{label}: no DownloadWillBegin after {secs}s; stuck task stack:")
    t.print_stack(file=sys.stdout)
    t.cancel()

async def scenario_A72(base):
    browser = await zendriver.start(headless=True)
    try:
        ctx_tab = await browser.create_context(base + "/docs/index.html")
        await ctx_tab.wait_for_ready_state("complete")
        await ctx_tab.set_download_path(WORK / "dirCtx")
        await click_dl(ctx_tab); await asyncio.sleep(2.5)
        print("A7.2 after set_download_path on ctx tab + click:", listing())
        async with ctx_tab.expect_download() as ex:
            await click_dl(ctx_tab)
            await wait_value(ex, "A7.2 ctx expect_download")
        # control: explicit browser_context_id
        await ctx_tab.send(cdp.browser.set_download_behavior(behavior="allow", download_path=str(WORK / "dirCtxExplicit"), browser_context_id=ctx_tab.target.browser_context_id, events_enabled=True))
        (WORK / "dirCtxExplicit").mkdir(exist_ok=True)
        fut = asyncio.get_running_loop().create_future()
        async def h(e):
            if not fut.done(): fut.set_result(e)
        ctx_tab.add_handler(cdp.browser.DownloadWillBegin, h)
        await click_dl(ctx_tab)
        try:
            e = await asyncio.wait_for(fut, 5); print("A7.2 control DownloadWillBegin with browser_context_id:", e.suggested_filename)
        except asyncio.TimeoutError:
            print("A7.2 control: no event")
        await asyncio.sleep(2)
        print("A7.2 control listing:", listing())
    finally:
        await browser.stop()

async def scenario_A73(base):
    browser = await zendriver.start(headless=True)
    try:
        tab = await browser.get(base + "/docs/index.html")
        await tab.wait_for_ready_state("complete")
        # control: link click inside expect_download
        async with tab.expect_download() as ex:
            await click_dl(tab)
            await wait_value(ex, "A7.3 control link click")
        async with tab.expect_download() as ex:
            await tab.download_file(base + "/docs/data.txt", "x.txt")
            await wait_value(ex, "A7.3 download_file inside expect_download")
        await asyncio.sleep(2)
        print("A7.3 listing (expectation meant deny):", listing())
    finally:
        await browser.stop()

async def scenario_A74(base):
    browser = await zendriver.start(headless=True)
    try:
        tab_a = await browser.get(base + "/docs/index.html")
        await tab_a.wait_for_ready_state("complete")
        await tab_a.set_download_path(WORK / "dirA")
        await click_dl(tab_a); await asyncio.sleep(2)
        print("A7.4 before: tab_a click ->", listing())
        tab_b = await browser.get(base + "/docs/index.html", new_tab=True)
        await tab_b.wait_for_ready_state("complete")
        await tab_b.download_file(base + "/docs/data.txt", "b.txt"); await asyncio.sleep(2)
        os.remove(WORK / "dirA" / "fromlink.txt")
        await click_dl(tab_a); await asyncio.sleep(2)
        print("A7.4 after tab_b.download_file, tab_a click ->", listing(), "tab_a._download_behavior=", tab_a._download_behavior)
    finally:
        await browser.stop()

async def scenario_A106(base):
    browser = await zendriver.start(headless=True)
    try:
        tab_a = await browser.get(base + "/docs/index.html")
        await tab_a.wait_for_ready_state("complete")
        tab_b = await browser.get(base + "/docs/index.html", new_tab=True)
        await tab_b.wait_for_ready_state("complete")
        await tab_b.set_download_path(WORK / "dirB")
        await tab_b.download_file(base + "/docs/data.txt", "first.txt"); await asyncio.sleep(2)
        print("A10.6 after first download in tab_b:", listing())
        async with tab_a.expect_download():
            pass
        print("A10.6 tab_b._download_behavior still:", tab_b._download_behavior)
        await tab_b.download_file(base + "/docs/data.txt", "second.txt"); await asyncio.sleep(3)
        print("A10.6 after expect_download on tab_a, second download in tab_b:", listing())
        # B16.9 variant: expectation with an actual click in tab_a, then tab_b download
        await tab_b.set_download_path(WORK / "dirB")
        async with tab_a.expect_download() as ex:
            await click_dl(tab_a)
            await wait_value(ex, "B16.9 tab_a expect_download")
        await tab_b.download_file(base + "/docs/data.txt", "third.txt"); await asyncio.sleep(3)
        print("B16.9 after tab_a expect_download+click, third download in tab_b:", listing())
    finally:
        await browser.stop()

async def main():
    srv, base = serve()
    try:
        for s in (scenario_A72, scenario_A73, scenario_A74, scenario_A106):
            shutil.rmtree(WORK / "downloads", ignore_errors=True)
            for sub in ("dirA", "dirB", "dirCtx", "dirCtxExplicit", "home/Downloads"):
                shutil.rmtree(WORK / sub, ignore_errors=True)
            print("=====", s.__name__)
            await asyncio.wait_for(s(base), 60)
    finally:
        srv.shutdown()

asyncio.run(asyncio.wait_for(main(), 250))
