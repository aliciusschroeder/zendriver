import asyncio, os, signal, zendriver as zd

async def main():
    browser = await zd.start(headless=True)
    tab = await browser.get("about:blank")
    await tab.evaluate("1")     # tab session attached
    proc = browser._process
    os.kill(proc.pid, signal.SIGSTOP)   # browser stops responding (hung)
    try:
        await asyncio.wait_for(browser.stop(), 10)
        print("stop() returned")
    except asyncio.TimeoutError:
        print("stop() did not return within 10s (terminate/kill fallback never reached)")
    print("process still alive:", proc.poll() is None)
    os.kill(proc.pid, signal.SIGCONT); proc.kill(); proc.wait()

asyncio.run(main())
