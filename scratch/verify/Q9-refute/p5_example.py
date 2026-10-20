import asyncio, sys, os
import zendriver as zd
pidfile = sys.argv[1]
async def main():
    async with await zd.start(headless=True) as browser:
        open(pidfile, "w").write(str(browser._process_pid))
        await browser.get("about:blank")
    print("block exited; browser.stopped =", browser.stopped)
asyncio.run(main())
print("asyncio.run returned")
