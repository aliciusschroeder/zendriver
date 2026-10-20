import asyncio, os, json
import zendriver as zd
from zendriver import cdp, SpecialKeys, KeyEvents, KeyPressEvent, KeyModifiers
HERE = os.path.dirname(os.path.abspath(__file__))
URL = "file://" + os.path.join(HERE, "keys.html")
async def main():
    browser = await zd.start(headless=True, browser_connection_timeout=1.0, browser_connection_max_tries=30)
    tab = await browser.get(URL)
    await tab.wait_for_ready_state("complete")
    ta = await tab.select("#ta")
    for s in ["👍", "👍🏽", "🇩🇪", "👨‍👩‍👧‍👦", "क्षि", "é", "é"]:
        await tab.evaluate("document.getElementById('ta').value=''")
        try:
            await ta.send_keys("x" + s + "y")
            r = await tab.evaluate("document.getElementById('ta').value")
            print(repr(s), "utf16 units:", len(s.encode('utf-16-le'))//2, "-> value", json.dumps(r), "OK" if r == "x"+s+"y" else "WRONG")
        except Exception as e:
            print(repr(s), "utf16 units:", len(s.encode('utf-16-le'))//2, "-> EXC", type(e).__name__, str(e).splitlines()[0])
    # SPACE code
    await tab.evaluate("window.__log=[]")
    await ta.send_keys(SpecialKeys.SPACE)
    print("SPACE log:", await tab.evaluate("window.__log"))
    # reuse of KeyEvents object
    ev = KeyEvents("A")
    p1 = ev.to_cdp_events(KeyPressEvent.DOWN_AND_UP); p2 = ev.to_cdp_events(KeyPressEvent.DOWN_AND_UP)
    print("reuse first keyDown text:", [p["text"] for p in p1 if p["type_"]=="keyDown"], "second:", [p["text"] for p in p2 if p["type_"]=="keyDown"])
    # ctrl+enter keyup
    await tab.evaluate("window.__log=[]")
    await ta.send_keys(KeyEvents.from_mixed_input([(SpecialKeys.ENTER, KeyModifiers.Ctrl)]))
    print("Ctrl+Enter log:", await tab.evaluate("window.__log"))
    await browser.stop()
asyncio.run(main())
