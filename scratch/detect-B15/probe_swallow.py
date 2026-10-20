import asyncio, zendriver as zd
from zendriver.core.connection import ProtocolException

HTML = """data:text/html,<html><body><div id=box><span>a</span></div>
<button id=hid style="display:none" onclick="window.clicked_hid=1">hid</button></body></html>"""

async def main():
    browser = await zd.start(headless=True)
    try:
        tab = await browser.get(HTML)
        await tab.wait_for_ready_state("complete")
        box = await tab.select("#box")
        # 1) invalid selector: tab-level raises, element-level silently returns empty
        try:
            r = await tab.query_selector_all("span[[")
            print("tab.query_selector_all invalid ->", r)
        except ProtocolException as e:
            print("tab.query_selector_all invalid -> raises ProtocolException:", str(e).splitlines()[0])
        print("box.query_selector_all invalid ->", await box.query_selector_all("span[["))
        print("box.query_selector invalid ->", await box.query_selector("span[["))
        # 2) JS exception inside Element.apply is dropped
        try:
            r = await box.apply("(e) => { throw new Error('boom from page') }")
            print("box.apply(throwing fn) returned:", repr(r))
        except Exception as e:
            print("box.apply raised", type(e).__name__, e)
        try:
            r = await tab.evaluate("(() => { throw new Error('boom from page') })()")
            print("tab.evaluate returned", r)
        except ProtocolException as e:
            print("tab.evaluate(throwing) -> raises ProtocolException (for contrast)")
        # 3) JS click on hidden element works when done directly
        await tab.evaluate("document.getElementById('hid').click()")
        print("direct JS click on hidden el sets flag:", await tab.evaluate("window.clicked_hid"))
    finally:
        await browser.stop()

asyncio.run(asyncio.wait_for(main(), 60))
