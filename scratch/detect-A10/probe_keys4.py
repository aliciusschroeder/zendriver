import asyncio, os, json
import zendriver as zd
from zendriver import cdp, SpecialKeys, KeyEvents, KeyPressEvent, KeyModifiers
HERE = os.path.dirname(os.path.abspath(__file__))
URL = "file://" + os.path.join(HERE, "keys.html")
async def main():
    for s in ["²", "٣"]:
        print(repr(s), [ (p["type_"], p["key"], p["code"], p["windows_virtual_key_code"]) for p in KeyEvents.from_text(s, KeyPressEvent.DOWN_AND_UP)])
    try:
        KeyEvents.from_mixed_input([("²", KeyModifiers.Shift)])
    except Exception as e:
        print("shift+²:", type(e).__name__, e)
    browser = await zd.start(headless=True, browser_connection_timeout=1.0, browser_connection_max_tries=30)
    tab = await browser.get(URL)
    await tab.wait_for_ready_state("complete")
    ta = await tab.select("#ta")
    for s in ["x²y", "x٣y"]:
        await tab.evaluate("document.getElementById('ta').value=''; window.__log=[]")
        try:
            await ta.send_keys(KeyEvents.from_mixed_input([s]))
            print(repr(s), "->", json.dumps(await tab.evaluate("document.getElementById('ta').value")), await tab.evaluate("window.__log"))
        except Exception as e:
            print(repr(s), "EXC", type(e).__name__, str(e).splitlines()[0])
    await browser.stop()
asyncio.run(main())
