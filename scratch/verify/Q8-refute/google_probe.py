import asyncio, sys, os
import zendriver
print("zendriver from", zendriver.__file__, "py", sys.version.split()[0])
async def main():
    browser = await zendriver.start(headless=True)
    try:
        info = browser.info
        print("browser.info keys:", list(dict(info).keys()) if info else info)
        tab = await browser.get("file://" + os.path.abspath("google.html"))
        await tab.sleep(1)
        brs = await tab.select_all("br[clear]")
        print("br[clear] in DOM:", [dict(b.attrs) for b in brs])
        center = await tab.select("center")
        print("center children tags:", [c.tag for c in center.children][:6])
        for c in center.children:
            try:
                await asyncio.wait_for(c.query_selector_all("a"), 10)
            except Exception as e:
                print(f"  child <{c.tag} id={c.attrs.get('id')}> .query_selector_all -> {type(e).__name__}: {e}")
        try:
            print("str(center)[:80]:", str(center)[:80])
        except Exception as e:
            print("str(center) ->", type(e).__name__, e)
    finally:
        await browser.stop()
asyncio.run(main())
