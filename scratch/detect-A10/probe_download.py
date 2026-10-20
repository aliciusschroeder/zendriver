import asyncio, threading, http.server, os, sys, shutil, glob
import zendriver as zd
HERE = os.path.dirname(os.path.abspath(__file__))
exec(open(os.path.join(HERE, "server_dl.py")).read())
DL = os.path.join(HERE, "dl_b"); shutil.rmtree(DL, ignore_errors=True); os.makedirs(DL)
async def main():
    browser = await zd.start(headless=True, browser_connection_timeout=1.0, browser_connection_max_tries=30)
    tab_a = browser.main_tab
    await tab_a.get(BASE + "/page")
    tab_b = await browser.get(BASE + "/page", new_tab=True)
    await tab_b.set_download_path(DL)
    await tab_b.download_file(BASE + "/file1", "first.bin")
    await asyncio.sleep(2)
    print("after first download in tab B:", sorted(os.listdir(DL)))
    # tab A uses expect_download (never touched download settings itself)
    async with tab_a.expect_download() as ex:
        pass
    print("tab_b._download_behavior still:", tab_b._download_behavior)
    await tab_b.download_file(BASE + "/file2", "second.bin")
    await asyncio.sleep(3)
    print("after second download in tab B:", sorted(os.listdir(DL)))
    await browser.stop()
asyncio.run(main())
