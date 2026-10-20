import asyncio, traceback
import zendriver as zd

async def main():
    browser = await zd.start(headless=True)
    tab = await browser.get("about:blank")
    await tab.evaluate("1 + 1")
    browser._process.kill()
    try:
        await asyncio.wait_for(browser.stop(), 20)
        print("stop ok")
    except BaseException as e:
        tb = traceback.extract_tb(e.__traceback__)
        for fs in tb:
            if "zendriver" in fs.filename:
                print(fs.filename.split("zendriver/")[-1], fs.name, fs.lineno)
        browser._process = None; browser._process_pid = None
        await browser._cleanup_temporary_profile()

asyncio.run(main())
