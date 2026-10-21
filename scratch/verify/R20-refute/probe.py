import asyncio, sys, os, json
import zendriver
from zendriver import cdp, SpecialKeys
HERE = os.path.dirname(os.path.abspath(__file__))
URL = "file://" + os.path.join(HERE, "page.html")

async def reset(tab):
    await tab.evaluate("window.submits=0; window.log=[]; document.getElementById('inp').value=''; document.getElementById('ta').value=''; document.getElementById('ce').innerHTML=''; true")

async def state(tab):
    return await tab.evaluate("JSON.stringify({submits: window.submits, inp: document.getElementById('inp').value, ta: document.getElementById('ta').value, ce: document.getElementById('ce').innerHTML, log: window.log})")

async def raw_chars(tab, el, chars):
    await el.apply("(e) => e.focus()")
    for c in chars:
        await tab.send(cdp.input_.dispatch_key_event("char", text=c))

async def main():
    print("zendriver from", zendriver.__file__, "python", sys.version.split()[0])
    browser = await zendriver.start(headless=True)
    try:
        ver = await browser.connection.send(cdp.browser.get_version())
        print("browser:", ver[1] if isinstance(ver, tuple) else ver)
        tab = await browser.get(URL)
        await tab.wait_for_ready_state("complete")
        inp = await tab.select("#inp"); ta = await tab.select("#ta"); ce = await tab.select("#ce")
        cases = [
            ("send_keys input 'abc\\n'", lambda: inp.send_keys("abc\n")),
            ("send_keys input 'abc\\r'", lambda: inp.send_keys("abc\r")),
            ("send_keys input 'abc\\r\\n'", lambda: inp.send_keys("abc\r\n")),
            ("send_keys input SpecialKeys.ENTER", lambda: inp.send_keys(SpecialKeys.ENTER)),
            ("raw char input '\\n'", lambda: raw_chars(tab, inp, ["a", "\n"])),
            ("raw char input '\\r'", lambda: raw_chars(tab, inp, ["a", "\r"])),
            ("OLD send_keys emulation list('abc\\r') on input", lambda: raw_chars(tab, inp, list("abc\r"))),
            ("OLD send_keys emulation list('abc\\n') on input", lambda: raw_chars(tab, inp, list("abc\n"))),
            ("send_keys textarea 'line1\\nline2\\rline3'", lambda: ta.send_keys("line1\nline2\rline3")),
            ("send_keys textarea 'a\\r\\nb'", lambda: ta.send_keys("a\r\nb")),
            ("raw char textarea '\\r'", lambda: raw_chars(tab, ta, ["a", "\r", "b"])),
            ("raw char textarea '\\n'", lambda: raw_chars(tab, ta, ["a", "\n", "b"])),
            ("send_keys contenteditable 'a\\nb'", lambda: ce.send_keys("a\nb")),
            ("raw char contenteditable '\\r'", lambda: raw_chars(tab, ce, ["a", "\r", "b"])),
        ]
        for name, fn in cases:
            await reset(tab)
            await asyncio.wait_for(fn(), 20)
            await asyncio.sleep(0.2)
            s = json.loads(await state(tab))
            log = [l for l in s.pop("log") if not l.startswith(("keyup",))]
            print(f"{name:55s} -> {s}  events={log[-4:]}")
    finally:
        await browser.stop()

asyncio.run(main())
