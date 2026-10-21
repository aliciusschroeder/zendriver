import asyncio, sys, pathlib
import zendriver
from zendriver import cdp, KeyEvents, KeyPressEvent
print("zendriver from", zendriver.__file__)
PAGE = pathlib.Path(__file__).with_name("page.html").resolve().as_uri()
async def main():
    browser = await zendriver.start(headless=True)
    try:
        tab = await browser.get(PAGE)
        await tab.wait_for_ready_state("complete")
        inp = await tab.select("#inp"); ta = await tab.select("#ta"); ce = await tab.select("#ce")
        async def st():
            return await tab.evaluate("JSON.stringify({submits: window.submits, inp: document.getElementById('inp').value, ta: document.getElementById('ta').value, ce: document.getElementById('ce').innerHTML})")
        async def reset():
            await tab.evaluate("window.submits=0; document.getElementById('inp').value=''; document.getElementById('ta').value=''; document.getElementById('ce').innerHTML=''; true")
        for label, el, arg in [
            ("send_keys(str) textarea 'line1\\nline2\\rline3'", ta, "line1\nline2\rline3"),
            ("send_keys(str) input 'abc\\n'", inp, "abc\n"),
            ("send_keys(str) input 'abc\\r'", inp, "abc\r"),
            ("send_keys(str) contenteditable 'a\\nb'", ce, "a\nb"),
            ("send_keys(from_mixed_input DOWN_AND_UP) textarea 'a\\nb'", ta, KeyEvents.from_mixed_input(["a\nb"])),
            ("send_keys(from_text CHAR) textarea 'a\\nb'", ta, KeyEvents.from_text("a\nb", KeyPressEvent.CHAR)),
        ]:
            await reset()
            await el.send_keys(arg)
            await asyncio.sleep(0.3)
            print(label, "->", await st())
    finally:
        await browser.stop()
asyncio.run(asyncio.wait_for(main(), 90))
