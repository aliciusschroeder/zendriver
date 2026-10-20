import asyncio, json, pathlib
import zendriver as zd
from zendriver import cdp
URL = pathlib.Path("page.html").resolve().as_uri()
async def main():
    b = await zd.start(headless=True)
    try:
        tab = await b.get(URL); await tab.wait_for_ready_state("complete")
        q = await tab.select("#q"); ta = await tab.select("#ta")
        await q.send_keys("hello\r")
        print("send_keys('hello\\r'): submitted=", await tab.evaluate("window.submitted"))
        await tab.evaluate("window.submitted=0")
        await q.apply("(e) => e.focus()")
        await tab.send(cdp.input_.dispatch_key_event("char", text="\r"))
        print("raw char '\\r' (what nodriver sent): submitted=", await tab.evaluate("window.submitted"))
        await ta.send_keys("x\ry")
        print("textarea send_keys('x\\ry') value=", json.dumps(await tab.evaluate("document.getElementById('ta').value")))
    finally:
        await b.stop()
asyncio.run(asyncio.wait_for(main(), 60))
