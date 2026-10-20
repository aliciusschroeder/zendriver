import asyncio, os, json
import zendriver as zd
from zendriver import cdp, SpecialKeys, KeyEvents, KeyPressEvent
HERE = os.path.dirname(os.path.abspath(__file__))
URL = "file://" + os.path.join(HERE, "keys.html")
async def reset(tab):
    await tab.evaluate("window.__log=[]; window.__sub=0; document.getElementById('i1').value=''; document.getElementById('ta').value=''")
async def main():
    browser = await zd.start(headless=True, browser_connection_timeout=1.0, browser_connection_max_tries=30)
    tab = await browser.get(URL)
    await tab.wait_for_ready_state("complete")
    i1 = await tab.select("#i1"); ta = await tab.select("#ta")
    print("payload for send_keys('\\n'):", KeyEvents.from_text("\n", KeyPressEvent.CHAR))
    for t in ["\n", "\r"]:
        await reset(tab)
        await ta.apply("(e)=>e.focus()")
        await tab.send(cdp.input_.dispatch_key_event(type_="char", text="a"))
        await tab.send(cdp.input_.dispatch_key_event(type_="char", text=t))
        await tab.send(cdp.input_.dispatch_key_event(type_="char", text="b"))
        print("raw char", repr(t), "textarea value:", json.dumps(await tab.evaluate("document.getElementById('ta').value")))
        await reset(tab)
        await i1.apply("(e)=>e.focus()")
        await tab.send(cdp.input_.dispatch_key_event(type_="char", text=t))
        print("raw char", repr(t), "input form submits:", await tab.evaluate("window.__sub"))
    await reset(tab)
    await ta.send_keys("line1\nline2\rline3")
    print("send_keys textarea 'line1\\nline2\\rline3' ->", json.dumps(await tab.evaluate("document.getElementById('ta').value")))
    await browser.stop()
asyncio.run(main())
