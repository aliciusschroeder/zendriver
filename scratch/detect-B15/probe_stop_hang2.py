import asyncio, os, signal, zendriver as zd

async def main():
    browser = await zd.start(headless=True)
    tab = await browser.get("about:blank")
    await tab.evaluate("1")
    proc = browser._process
    os.kill(proc.pid, signal.SIGSTOP)
    t = asyncio.create_task(browser.stop())
    await asyncio.sleep(5)
    print("done:", t.done())
    t.print_stack()
    t.cancel()
    os.kill(proc.pid, signal.SIGCONT); proc.kill(); proc.wait()

asyncio.run(main())
