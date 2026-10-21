import asyncio, copy, pickle, sys
import zendriver
print("zendriver from", zendriver.__file__)
async def main():
    browser = await zendriver.start(headless=True)
    try:
        tab = await browser.get("data:text/html,<div id=a class='x y'>hi</div>")
        el = await tab.select('#a')
        print("get class:", el.get('class'))
        for name, fn in [("copy", copy.copy), ("deepcopy", copy.deepcopy), ("pickle", lambda e: pickle.loads(pickle.dumps(e)))]:
            try:
                r = await asyncio.wait_for(asyncio.to_thread(lambda: None), 5)
                d = fn(el); print(name, "OK", d.get('id'), d.tab is el.tab)
            except BaseException as e:
                print(name, type(e).__name__, str(e)[:100])
        print("original still works:", await asyncio.wait_for(el.apply("(e)=>e.id"), 10))
    finally:
        await browser.stop()
asyncio.run(main())
