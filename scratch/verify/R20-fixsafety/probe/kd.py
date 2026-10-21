import asyncio, sys, pathlib
import zendriver as zd
print("zendriver from", zd.__file__)
async def main():
    b = await zd.start(headless=True)
    try:
        tab = await b.get("data:text/html,<input id=i><script>window.ev=[];for(const t of ['keydown','keypress','keyup']) i.addEventListener(t,e=>ev.push(t+':'+e.key))</script>")
        await tab.wait_for_ready_state("complete")
        i = await tab.select("#i")
        await i.send_keys("q\n")
        print("send_keys('q\\n') events:", await tab.evaluate("JSON.stringify(window.ev)"))
    finally:
        await b.stop()
asyncio.run(asyncio.wait_for(main(), 60))
