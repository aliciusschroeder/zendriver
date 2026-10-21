"""Sweep: quiet page schedules window.close() after D ms, then `await tab` immediately. Which D hang?"""
import asyncio, sys, time
import zendriver
print("zendriver from", zendriver.__file__, "python", sys.version.split()[0])
PAGE = "data:text/html,<title>q</title><p>q</p>"

async def main():
    browser = await zendriver.start(headless=True)
    try:
        for d in [0, 20, 40, 60, 80, 100, 130, 160, 200, 250]:
            res = []
            for _ in range(2):
                tab = await browser.get(PAGE, new_tab=True)
                await tab.evaluate("1")
                await tab.evaluate(f"setTimeout(() => window.close(), {d}); 1")
                t0 = time.monotonic()
                w = asyncio.create_task(tab.wait())
                await asyncio.wait({w}, timeout=3)
                if w.done():
                    e = w.exception()
                    res.append("raise" if e else "ok")
                else:
                    res.append("HANG")
                    w.cancel()
                    try: await w
                    except BaseException: pass
            print(f"delay {d:4d} ms: {res}")
    finally:
        await browser.stop()
asyncio.run(main())
