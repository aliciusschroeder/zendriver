import asyncio, os, json
import zendriver as zd
from zendriver import SpecialKeys, KeyEvents, KeyPressEvent, KeyModifiers
HERE = os.path.dirname(os.path.abspath(__file__))
URL = "file://" + os.path.join(HERE, "keys.html")

async def reset(tab):
    await tab.evaluate("window.__log=[]; window.__sub=0; document.getElementById('i1').value=''; document.getElementById('ta').value=''")

async def main():
    browser = await zd.start(headless=True, browser_connection_timeout=1.0, browser_connection_max_tries=30)
    tab = await browser.get(URL)
    await tab.wait_for_ready_state("complete")
    i1 = await tab.select("#i1"); ta = await tab.select("#ta")

    await reset(tab)
    await i1.send_keys(SpecialKeys.ENTER)
    print("A ENTER(DOWN_AND_UP) log:", await tab.evaluate("window.__log"), "submits:", await tab.evaluate("window.__sub"))

    await reset(tab)
    await i1.send_keys(SpecialKeys.TAB)
    print("B TAB log:", await tab.evaluate("window.__log"), "active:", await tab.evaluate("document.activeElement.id"))

    await reset(tab)
    await i1.send_keys("abc\n")
    print("C 'abc\\n' submits:", await tab.evaluate("window.__sub"), "log:", await tab.evaluate("window.__log"))

    await reset(tab)
    await i1.send_keys("abc\r")
    print("C2 'abc\\r' submits:", await tab.evaluate("window.__sub"))

    await reset(tab)
    await ta.send_keys("a\r\nb")
    print("D textarea 'a\\r\\nb' value:", json.dumps(await tab.evaluate("document.getElementById('ta').value")))
    await reset(tab)
    await ta.send_keys("a\nb")
    print("D2 textarea 'a\\nb' value:", json.dumps(await tab.evaluate("document.getElementById('ta').value")))

    await reset(tab)
    await ta.send_keys(KeyEvents.from_mixed_input(["A!"]))
    print("E 'A!' DOWN_AND_UP log:", await tab.evaluate("window.__log"), "value:", json.dumps(await tab.evaluate("document.getElementById('ta').value")))

    await reset(tab)
    await ta.send_keys(KeyEvents.from_text("a\r\nb", KeyPressEvent.DOWN_AND_UP))
    print("F textarea DOWN_AND_UP 'a\\r\\nb' value:", json.dumps(await tab.evaluate("document.getElementById('ta').value")))
    await browser.stop()

asyncio.run(main())
