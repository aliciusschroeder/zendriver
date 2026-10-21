import asyncio, sys
sys.path.insert(0, __import__("os").path.dirname(__file__))
import zendriver as zd
from zendriver import KeyEvents, KeyPressEvent, SpecialKeys, KeyModifiers
from helpers import serve
print("zendriver from", zd.__file__, "python", sys.version.split()[0])

async def main():
    httpd, base = serve()
    browser = await zd.start(headless=True)
    try:
        tab = await browser.get(base + "/keys.html")
        await tab.wait_for_ready_state("complete")
        ta = await tab.select("#t")
        async def reset():
            await tab.evaluate("document.getElementById('t').value=''; window.log=[]")
        # A10.5
        for s in ["👍", "👍🏽", "🇩🇪", "👨‍👩‍👧‍👦", "é", "á̂̃"]:
            await reset()
            try:
                await ta.send_keys("x" + s + "y")
                r = "OK"
            except Exception as e:
                r = f"EXC {type(e).__name__}: {e}"
            val = await tab.evaluate("document.getElementById('t').value")
            print("A10.5", repr(s), "utf16", len(s.encode('utf-16-le'))//2, "->", r, "value=", repr(val))
        # A10.9
        for label, seq in [("Ctrl+Enter", [(SpecialKeys.ENTER, KeyModifiers.Ctrl)]), ("A", ["A"]), ("Ctrl+Shift+a", [("a", KeyModifiers.Ctrl|KeyModifiers.Shift)])]:
            await reset()
            await ta.send_keys(KeyEvents.from_mixed_input(seq))
            print("A10.9", label, await tab.evaluate("JSON.stringify(window.log)"))
        # A10.11
        for label, payload in [("SPACE", SpecialKeys.SPACE), ("TAB", SpecialKeys.TAB)]:
            await reset()
            await ta.send_keys(payload)
            print("A10.11", label, await tab.evaluate("JSON.stringify(window.log)"), "value=", repr(await tab.evaluate("document.getElementById('t').value")))
        await reset()
        await ta.send_keys(KeyEvents.from_mixed_input([" "]))
        print("A10.11 mixed ' '", await tab.evaluate("JSON.stringify(window.log)"))
        # A10.10 reuse in real browser
        await reset()
        ev = KeyEvents("A")
        await ta.send_keys(ev.to_cdp_events(KeyPressEvent.DOWN_AND_UP))
        await ta.send_keys(ev.to_cdp_events(KeyPressEvent.DOWN_AND_UP))
        print("A10.10 reuse value=", repr(await tab.evaluate("document.getElementById('t').value")))
    finally:
        await browser.stop()
        httpd.shutdown()

asyncio.run(asyncio.wait_for(main(), 90))
