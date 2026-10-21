import asyncio, os, sys, pathlib
import zendriver
from zendriver import cdp
print("zendriver from", zendriver.__file__, "python", sys.version.split()[0])
PAGE = pathlib.Path(__file__).with_name("page.html").resolve().as_uri()

async def reset(tab):
    await tab.evaluate("window.submits=0; window.keylog=[]; document.getElementById('inp').value=''; document.getElementById('ta').value=''; document.getElementById('ce').innerHTML=''; true")

async def state(tab):
    return await tab.evaluate("JSON.stringify({submits: window.submits, inp: document.getElementById('inp').value, ta: document.getElementById('ta').value, ce: document.getElementById('ce').innerHTML, log: window.keylog})")

async def main():
    browser = await zendriver.start(headless=True)
    try:
        tab = await browser.get(PAGE)
        await tab.wait_for_ready_state("complete")
        inp = await tab.select("#inp"); ta = await tab.select("#ta"); ce = await tab.select("#ce")
        print("chrome version:", (await browser.connection.send(cdp.browser.get_version()))[1])
        cases = [
            ("send_keys input 'abc\\n'", inp, "abc\n"),
            ("send_keys input 'abc\\r'", inp, "abc\r"),
            ("send_keys input 'abc\\r\\n'", inp, "abc\r\n"),
            ("send_keys textarea 'line1\\nline2\\rline3'", ta, "line1\nline2\rline3"),
            ("send_keys textarea 'a\\r\\nb'", ta, "a\r\nb"),
            ("send_keys contenteditable 'a\\nb'", ce, "a\nb"),
        ]
        for label, el, text in cases:
            await reset(tab)
            await el.send_keys(text)
            await asyncio.sleep(0.3)
            print(label, "->", await state(tab))
        # Raw controls
        for label, el, ch in [("raw char '\\n' into textarea after 'a'", ta, "\n"), ("raw char '\\r' into textarea after 'a'", ta, "\r"),
                               ("raw char '\\n' into input after 'abc'", inp, "\n"), ("raw char '\\r' into input after 'abc'", inp, "\r")]:
            await reset(tab)
            await el.send_keys("a" if el is ta else "abc")
            await tab.send(cdp.input_.dispatch_key_event(type_="char", text=ch))
            if el is ta:
                await tab.send(cdp.input_.dispatch_key_event(type_="char", text="b"))
            await asyncio.sleep(0.3)
            print(label, "->", await state(tab))
        # SpecialKeys.ENTER path (DOWN_AND_UP) for comparison
        await reset(tab)
        await inp.send_keys("abc"); await inp.send_keys(zendriver.SpecialKeys.ENTER)
        await asyncio.sleep(0.3)
        print("send_keys input 'abc' + SpecialKeys.ENTER ->", await state(tab))
    finally:
        await browser.stop()

asyncio.run(asyncio.wait_for(main(), 90))
