import asyncio, sys
import zendriver
print("zendriver from", zendriver.__file__)
async def main():
    browser = await zendriver.start(headless=True)
    try:
        tab = await browser.get("data:text/html,<div id=x>plain</div>")
        el = await tab.select('#x')
        b0 = el.backend_node_id
        el.attrs['data-x'] = '1'
        await asyncio.wait_for(el.save_to_dom(), 10)
        print("backend id before/after:", b0, el.backend_node_id, "outerHTML:", await tab.evaluate("document.getElementById('x').outerHTML"))
        try:
            print("apply after save_to_dom:", await asyncio.wait_for(el.apply("(e)=>e.isConnected"), 10))
        except Exception as e:
            print("apply after save_to_dom EXC", type(e).__name__, str(e).splitlines()[0])
    finally:
        await browser.stop()
asyncio.run(main())
