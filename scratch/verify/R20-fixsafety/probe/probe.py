import asyncio, sys, pathlib
import zendriver as zd
from zendriver import cdp
print("zendriver from", zd.__file__)
PAGE = pathlib.Path(sys.argv[1]).as_uri()

async def reset(tab):
    await tab.evaluate("document.getElementById('inp').value='';document.getElementById('ta').value='';document.getElementById('ce').innerHTML='';window.submits=0;window.kp=[];")

async def raw_char(tab, el, text):
    await el.apply("(e)=>e.focus()")
    await tab.send(cdp.input_.dispatch_key_event(type_="char", text=text))

async def main():
    b = await zd.start(headless=True)
    try:
        tab = await b.get(PAGE)
        await tab.wait_for_ready_state("complete")
        inp = await tab.select("#inp"); ta = await tab.select("#ta"); ce = await tab.select("#ce")
        for label, fn in [
            ("raw char '\\n' textarea", lambda: raw_char(tab, ta, "\n")),
            ("raw char '\\r' textarea", lambda: raw_char(tab, ta, "\r")),
            ("raw char '\\r\\n' textarea", lambda: raw_char(tab, ta, "\r\n")),
            ("raw char '\\n' input", lambda: raw_char(tab, inp, "\n")),
            ("raw char '\\r' input", lambda: raw_char(tab, inp, "\r")),
            ("raw char '\\r\\n' input", lambda: raw_char(tab, inp, "\r\n")),
            ("send_keys textarea 'line1\\nline2\\rline3\\r\\nline4'", lambda: ta.send_keys("line1\nline2\rline3\r\nline4")),
            ("send_keys input 'abc\\n'", lambda: inp.send_keys("abc\n")),
            ("send_keys input 'abc\\r'", lambda: inp.send_keys("abc\r")),
            ("send_keys input SpecialKeys.ENTER", lambda: inp.send_keys(zd.SpecialKeys.ENTER)),
            ("send_keys ce 'a\\nb'", lambda: ce.send_keys("a\nb")),
        ]:
            await reset(tab)
            await fn()
            await asyncio.sleep(0.2)
            r = await tab.evaluate("JSON.stringify({inp:document.getElementById('inp').value, ta:document.getElementById('ta').value, ce:document.getElementById('ce').innerHTML, submits:window.submits, kp:window.kp})")
            print(f"{label:55s} -> {r}")
    finally:
        await b.stop()

asyncio.run(asyncio.wait_for(main(), 90))
