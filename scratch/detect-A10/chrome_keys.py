import asyncio, json, pathlib
import zendriver as zd
from zendriver import KeyEvents, SpecialKeys, KeyModifiers, KeyPressEvent
URL = pathlib.Path("page.html").resolve().as_uri()
async def reset(tab):
    await tab.evaluate("window.log=[]; window.submitted=0; document.getElementById('q').value=''; document.getElementById('ta').value=''; document.getElementById('i2').value=''")
async def main():
    b = await zd.start(headless=True)
    try:
        tab = await b.get(URL)
        await tab.wait_for_ready_state("complete")
        q = await tab.select("#q"); ta = await tab.select("#ta"); i2 = await tab.select("#i2")
        await reset(tab); await q.send_keys("hello\n")
        print("1 input send_keys('hello\\n'): submitted=", await tab.evaluate("window.submitted"), "value=", json.dumps(await tab.evaluate("document.getElementById('q').value")))
        await reset(tab); await q.send_keys("hello\r\n")
        print("1b input send_keys('hello\\r\\n'): submitted=", await tab.evaluate("window.submitted"), "value=", json.dumps(await tab.evaluate("document.getElementById('q').value")))
        await reset(tab); await q.send_keys(SpecialKeys.ENTER)
        print("1c input send_keys(ENTER): submitted=", await tab.evaluate("window.submitted"))
        await reset(tab); await ta.send_keys("a\nb")
        print("2 textarea 'a\\nb' value=", json.dumps(await tab.evaluate("document.getElementById('ta').value")))
        await reset(tab); await ta.send_keys("a\r\nb")
        print("3 textarea 'a\\r\\nb' value=", json.dumps(await tab.evaluate("document.getElementById('ta').value")))
        await reset(tab); await ta.send_keys(KeyEvents.from_mixed_input(["a\nb"]))
        print("3b textarea DOWN_AND_UP 'a\\nb' value=", json.dumps(await tab.evaluate("document.getElementById('ta').value")))
        await reset(tab); await ta.send_keys(KeyEvents.from_mixed_input(["a\r\nb"]))
        print("3c textarea DOWN_AND_UP 'a\\r\\nb' value=", json.dumps(await tab.evaluate("document.getElementById('ta').value")))
        await reset(tab); await i2.send_keys(SpecialKeys.SPACE)
        print("4 SPACE log=", await tab.evaluate("JSON.stringify(window.log)"))
        await reset(tab); await i2.send_keys(SpecialKeys.ENTER)
        print("4b ENTER log=", await tab.evaluate("JSON.stringify(window.log)"))
        for name, mod in (("Alt", KeyModifiers.Alt), ("Meta", KeyModifiers.Meta), ("Ctrl", KeyModifiers.Ctrl)):
            await reset(tab); await i2.send_keys(KeyEvents.from_mixed_input([("k", mod)]))
            print(f"5 {name}+k value=", json.dumps(await tab.evaluate("document.getElementById('i2').value")), "log=", await tab.evaluate("JSON.stringify(window.log)"))
    finally:
        await b.stop()
asyncio.run(asyncio.wait_for(main(), 90))
