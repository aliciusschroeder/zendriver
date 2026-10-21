import asyncio, sys, os, warnings, traceback
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import zendriver as zd
from zendriver import cdp
from helpers import serve
warnings.simplefilter("ignore")
print("zendriver from", zd.__file__, "python", sys.version.split()[0])
DL = os.path.join(HERE, "dl"); HOME_DL = os.path.expanduser("~/Downloads")
def ls(d): return sorted(os.listdir(d)) if os.path.isdir(d) else []
def mine_home(): return [f for f in ls(HOME_DL) if f.startswith("beref_")]

async def click_dl(tab, name):
    await tab.evaluate(f"document.getElementById('dl').download={name!r}; document.getElementById('dl').click()")

async def with_browser(fn):
    browser = await zd.start(headless=True)
    try:
        await asyncio.wait_for(fn(browser), 40)
    except Exception:
        traceback.print_exc()
    finally:
        await browser.stop()

async def main():
    httpd, base = serve(); page = base + "/docs/index.html"
    wd = os.path.join(HERE, "work", "r31"); os.makedirs(wd, exist_ok=True); os.chdir(wd)
    async def a72(browser):
        print("== A7.2 context tab")
        ctx = await browser.create_context(page); await ctx.wait_for_ready_state("complete")
        d = os.path.join(DL, "a72"); await ctx.set_download_path(d)
        await click_dl(ctx, "beref_a72_link.txt"); await asyncio.sleep(2.5)
        print("  set_download_path on ctx tab, click ->", ls(d), "home:", mine_home())
        try:
            async with ctx.expect_download() as ex:
                await click_dl(ctx, "beref_a72_expect.txt")
                v = await asyncio.wait_for(ex.value, 5)
                print("  ctx expect_download ->", v.suggested_filename)
        except asyncio.TimeoutError:
            print("  ctx expect_download -> TIMEOUT (no DownloadWillBegin within 5s)")
        await asyncio.sleep(1)
        # control: explicit browser_context_id
        d2 = os.path.join(DL, "a72ctl"); os.makedirs(d2, exist_ok=True)
        await ctx.send(cdp.browser.set_download_behavior("allow", browser_context_id=ctx.target.browser_context_id, download_path=d2))
        await click_dl(ctx, "beref_a72_ctl.txt"); await asyncio.sleep(2.5)
        print("  control with browser_context_id ->", ls(d2))
        # was the default context changed? main tab click
        mt = await browser.get(page); await mt.wait_for_ready_state("complete")
        await click_dl(mt, "beref_a72_main.txt"); await asyncio.sleep(2.5)
        print("  main tab (default ctx, never set path itself) click ->", "a72:", ls(d), "home:", mine_home())
    async def a73(browser):
        print("== A7.3 download_file inside expect_download")
        tab = await browser.get(page); await tab.wait_for_ready_state("complete")
        try:
            async with tab.expect_download() as ex:
                await tab.download_file(base + "/docs/data.txt", "beref_a73.txt")
                v = await asyncio.wait_for(ex.value, 5)
                print("  ex.value ->", v.suggested_filename)
        except asyncio.TimeoutError:
            print("  ex.value -> TIMEOUT (no DownloadWillBegin within 5s)")
        await asyncio.sleep(1.5)
        print("  ./downloads:", ls(os.path.join(wd, "downloads")))
        # set_download_path inside
        try:
            async with tab.expect_download() as ex:
                await tab.set_download_path(os.path.join(DL, "a73b"))
                await click_dl(tab, "beref_a73b.txt")
                v = await asyncio.wait_for(ex.value, 5)
                print("  set_download_path inside -> event", v.suggested_filename)
        except asyncio.TimeoutError:
            print("  set_download_path inside -> TIMEOUT")
        await asyncio.sleep(1.5); print("  a73b:", ls(os.path.join(DL, "a73b")))
        # control: expect_download alone after path set
        try:
            async with tab.expect_download() as ex:
                await click_dl(tab, "beref_a73c.txt")
                v = await asyncio.wait_for(ex.value, 5)
                print("  control expect_download + click -> event", v.suggested_filename)
        except asyncio.TimeoutError:
            print("  control -> TIMEOUT")
    async def a74(browser):
        print("== A7.4 tab_b.download_file clobbers tab_a path")
        ta = await browser.get(page); await ta.wait_for_ready_state("complete")
        da = os.path.join(DL, "a74a"); await ta.set_download_path(da)
        await click_dl(ta, "beref_a74_before.txt"); await asyncio.sleep(2)
        print("  tab_a before:", ls(da))
        tb = await browser.get(page, new_tab=True); await tb.wait_for_ready_state("complete")
        await tb.download_file(base + "/docs/data.txt", "beref_a74_b.txt"); await asyncio.sleep(2)
        await click_dl(ta, "beref_a74_after.txt"); await asyncio.sleep(2)
        print("  dirA:", ls(da), "./downloads:", ls(os.path.join(wd, "downloads")))
    async def a106(browser):
        print("== A10.6/B16.9 expect_download on tab_a resets tab_b path")
        tb = await browser.get(page); await tb.wait_for_ready_state("complete")
        db = os.path.join(DL, "a106b"); await tb.set_download_path(db)
        await tb.download_file(base + "/docs/data.txt", "beref_a106_first.txt"); await asyncio.sleep(2)
        print("  dirB after first:", ls(db))
        ta = await browser.get(page, new_tab=True); await ta.wait_for_ready_state("complete")
        async with ta.expect_download():
            pass
        print("  tb._download_behavior:", tb._download_behavior[0])
        await tb.download_file(base + "/docs/data.txt", "beref_a106_second.txt"); await asyncio.sleep(2.5)
        print("  dirB after second:", ls(db), "home:", mine_home())
    for fn in (a72, a73, a74, a106):
        await with_browser(fn)
    httpd.shutdown()

asyncio.run(asyncio.wait_for(main(), 200))
