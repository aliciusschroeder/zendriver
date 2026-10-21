import asyncio, sys, json
import zendriver
from zendriver import cdp
from zendriver.core.keys import KeyEvents, KeyPressEvent, SpecialKeys, KeyModifiers
from zendriver.core.connection import ProtocolException
from common import serve
print("zendriver:", zendriver.__file__)

async def main():
    srv, base = serve()
    browser = await zendriver.start(headless=True)
    try:
        tab = await browser.get(base + "/keys.html")
        await tab.wait_for_ready_state("complete")
        ta = await tab.select("#t")
        # A10.5
        for s in ['\U0001F44D', '\U0001F44D\U0001F3FD', '\U0001F1E9\U0001F1EA', '\U0001F468‍\U0001F469‍\U0001F467‍\U0001F466']:
            await tab.evaluate("document.getElementById('t').value=''")
            try:
                await asyncio.wait_for(ta.send_keys('x' + s + 'y'), 15)
                res = 'OK'
            except ProtocolException as e:
                res = f'EXC ProtocolException {e}'
            val = await tab.evaluate("document.getElementById('t').value")
            print(f"A10.5 {s!r} utf16={len(s.encode('utf-16-le'))//2} -> {res!r}; value={val!r}")
        # from_mixed_input path too
        await tab.evaluate("document.getElementById('t').value=''")
        try:
            await ta.send_keys(KeyEvents.from_mixed_input(['Hi \U0001F44D\U0001F3FD!']))
            print("A10.5 from_mixed_input OK")
        except ProtocolException as e:
            print("A10.5 from_mixed_input EXC", e, "value=", await tab.evaluate("document.getElementById('t').value"))

        async def logged(payloads, label):
            await tab.evaluate("window.log=[]; document.getElementById('t').value=''")
            await ta.send_keys(payloads)
            log = await tab.evaluate("window.log")
            print(label, json.dumps(log))
        # A10.9
        await logged(KeyEvents.from_mixed_input(['A']), "A10.9 'A':")
        await logged(KeyEvents.from_mixed_input([(SpecialKeys.ENTER, KeyModifiers.Ctrl)]), "A10.9 Ctrl+Enter:")
        await logged(KeyEvents.from_mixed_input([("a", KeyModifiers.Ctrl | KeyModifiers.Shift)]), "A10.9 Ctrl+Shift+a:")
        # A10.11
        await logged(SpecialKeys.SPACE, "A10.11 SpecialKeys.SPACE:")
        await logged(KeyEvents.from_mixed_input([' ']), "A10.11 from_mixed_input(' '):")
        await logged(SpecialKeys.TAB, "A10.11 control TAB:")
        # A10.10 reuse in browser
        ev = KeyEvents('A')
        await logged(ev.to_cdp_events(KeyPressEvent.DOWN_AND_UP), "A10.10 first use:")
        await logged(ev.to_cdp_events(KeyPressEvent.DOWN_AND_UP), "A10.10 second use:")
        print("A10.10 textarea after second:", await tab.evaluate("document.getElementById('t').value"))
    finally:
        await browser.stop()
        srv.shutdown()

asyncio.run(asyncio.wait_for(main(), 100))
