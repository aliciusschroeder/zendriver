import asyncio, zendriver as zd

HTML = """data:text/html,<html><body>
<button id=vis onclick="window.clicked_vis=1">vis</button>
<button id=hid style="display:none" onclick="window.clicked_hid=1">hid</button>
<input id=file type=file style="display:none" onclick="window.clicked_file=1">
</body></html>"""

async def main():
    browser = await zd.start(headless=True)
    try:
        tab = await browser.get(HTML)
        await tab.wait_for_ready_state("complete")
        vis = await tab.select("#vis")
        await vis.click()
        print("visible clicked:", await tab.evaluate("window.clicked_vis"))
        hid = await tab.select("#hid")
        try:
            await hid.click()
            print("hidden click ok, clicked=", await tab.evaluate("window.clicked_hid"))
        except Exception as e:
            print("hidden click raised:", type(e).__name__, repr(str(e))[:200])
            print("JS el.click would have worked; clicked_hid =", await tab.evaluate("window.clicked_hid"))
        try:
            pos = await hid.get_position()
            print("get_position:", pos)
        except Exception as e:
            print("get_position raised:", type(e).__name__, str(e)[:100])
        try:
            await hid.mouse_click()
            print("mouse_click returned normally")
        except Exception as e:
            print("mouse_click raised:", type(e).__name__, str(e)[:100])
        try:
            await hid.screenshot_b64()
        except Exception as e:
            print("screenshot_b64 raised:", type(e).__name__, "(docstring promises RuntimeError)")
    finally:
        await browser.stop()

asyncio.run(asyncio.wait_for(main(), 60))
