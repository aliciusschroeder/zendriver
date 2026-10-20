import asyncio, sys, time
import zendriver
import zendriver.core.util as zutil
print("zendriver from", zendriver.__file__)
async def main():
    for args, kw in [([], {}), ([], dict(browser_connection_max_tries=120)),
                     (["--headless=new", "--no-sandbox"], dict(browser_connection_max_tries=120))]:
        t = time.monotonic()
        try:
            b = await zendriver.start(headless=True, browser_args=args, **kw)
        except Exception as e:
            print(args, kw, "FAILED after %.1fs" % (time.monotonic() - t), type(e).__name__)
            continue
        print(args, kw, "OK after %.1fs" % (time.monotonic() - t))
        await b.stop()
asyncio.run(asyncio.wait_for(main(), 100))
