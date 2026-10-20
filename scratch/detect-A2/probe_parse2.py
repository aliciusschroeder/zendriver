import asyncio
import zendriver as zd
from zendriver import cdp

def custom_cmd():
    json = yield {"method": "Target.getTargets", "params": {}}
    return json["notThere"]

async def main():
    browser = await zd.start(headless=True)
    try:
        tab = await browser.get("about:blank")
        await tab.send(cdp.runtime.evaluate("0"))
        try:
            await asyncio.wait_for(browser.connection.send(custom_cmd()), 5)
        except asyncio.TimeoutError:
            print("browser.connection.send HUNG instead of raising KeyError")
        print("browser listener running:", browser.connection.listener.running)
        try:
            r = await asyncio.wait_for(tab.send(cdp.runtime.evaluate("2+2")), 5)
            print("tab send ok", r[0].value)
        except asyncio.TimeoutError:
            print("tab.send HUNG too: tab listener running:", tab.listener.running, "inbox size", tab._inbox.qsize())
        try:
            r = await asyncio.wait_for(tab.evaluate("1+1"), 5)
            print("tab.evaluate ok", r)
        except asyncio.TimeoutError:
            print("tab.evaluate HUNG")
        await browser.connection.send(cdp.target.get_targets())
        r = await asyncio.wait_for(tab.send(cdp.runtime.evaluate("3+3")), 5)
        print("after a browser-level send, tab send ok:", r[0].value)
    finally:
        await browser.stop()

asyncio.run(asyncio.wait_for(main(), 50))
