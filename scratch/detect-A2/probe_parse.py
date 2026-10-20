import asyncio
import zendriver as zd
from zendriver import cdp

def custom_cmd():
    # a user-defined command whose response parsing fails (e.g. protocol drift)
    json = yield {"method": "Runtime.evaluate", "params": {"expression": "1"}}
    return json["notThere"]

async def main():
    browser = await zd.start(headless=True)
    try:
        tab = await browser.get("about:blank")
        await tab.send(cdp.runtime.evaluate("0"))
        old_listener = tab.listener
        try:
            r = await asyncio.wait_for(tab.send(custom_cmd()), 5)
            print("returned", r)
        except asyncio.TimeoutError:
            print("send() HUNG: timed out after 5s instead of raising KeyError")
        print("old listener running:", old_listener.running, "task exc:", old_listener.task.exception() if old_listener.task.done() else None)
        print("mapper size:", len(tab.mapper))
        r = await asyncio.wait_for(tab.send(cdp.runtime.evaluate("2+2")), 5)
        print("next send ok", r[0].value, "new listener?", tab.listener is not old_listener)
    finally:
        await browser.stop()

asyncio.run(asyncio.wait_for(main(), 50))
