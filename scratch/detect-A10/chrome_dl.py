import asyncio, pathlib, shutil
import zendriver as zd
URL = pathlib.Path("dl.html").resolve().as_uri()
dirA = pathlib.Path("dl_A").resolve(); shutil.rmtree(dirA, ignore_errors=True)
async def main():
    b = await zd.start(headless=True)
    try:
        tab1 = await b.get(URL)
        await tab1.wait_for_ready_state("complete")
        await tab1.set_download_path(dirA)
        await tab1.evaluate("document.getElementById('d1').click()")
        await asyncio.sleep(2)
        print("after first download, dirA:", sorted(p.name for p in dirA.iterdir()))
        tab2 = await b.get("about:blank", new_tab=True)
        async with tab2.expect_download():
            pass
        print("tab1._download_behavior still:", tab1._download_behavior)
        await tab1.evaluate("document.getElementById('d2').click()")
        await asyncio.sleep(2)
        print("after second download, dirA:", sorted(p.name for p in dirA.iterdir()))
        # control: same, but without tab2.expect_download
    finally:
        await b.stop()
asyncio.run(asyncio.wait_for(main(), 60))
