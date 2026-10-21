import asyncio, sys, time
import zendriver as zd

async def main() -> None:
    print("zendriver from", zd.__file__)
    browser = await zd.start(headless=True, browser_args=["--enable-logging=stderr"])
    tab = browser.main_tab
    hung = False
    for i in range(int(sys.argv[1])):
        try:
            await asyncio.wait_for(tab.evaluate("console.log('x'.repeat(1000)); 1+1"), 10)
        except asyncio.TimeoutError:
            print(f"round {i}: TIMEOUT")
            hung = True
            break
    print("RESULT hung", hung, "rounds", i + 1)
    t = time.monotonic()
    try:
        await asyncio.wait_for(browser.stop(), 20)
        print(f"stop ok in {time.monotonic() - t:.1f}s")
    except asyncio.TimeoutError:
        print("stop TIMEOUT")
        browser._process.kill()

asyncio.run(main())
