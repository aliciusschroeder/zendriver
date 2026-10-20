import asyncio, traceback, warnings
warnings.simplefilter("ignore")
import zendriver
print("zendriver from", zendriver.__file__)
async def main():
    browser = await zendriver.start(headless=True)
    try:
        tab = await browser.get("data:text/html,<body><br id=b clear=all><x-list id=x items=3></x-list></body>")
        br = await tab.select("#b")
        try:
            await asyncio.wait_for(br.update(), 20)
        except TypeError:
            traceback.print_exc(limit=-3)
        x = await tab.select("#x")
        try:
            repr(x)
        except TypeError:
            traceback.print_exc(limit=-3)
    finally:
        await browser.stop()
asyncio.run(main())
