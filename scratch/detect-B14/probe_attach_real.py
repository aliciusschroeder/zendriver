import asyncio
import zendriver as zd
from zendriver import cdp
from zendriver.core.connection import ProtocolException

async def main():
    browser = await zd.start(headless=True)
    res = {}
    try:
        for i in range(15):
            tid = await browser.connection.send(cdp.target.create_target("about:blank"))
            tab = await browser._get_tab(tid)
            async def ev():
                try:
                    await asyncio.wait_for(tab.evaluate("1"), 3); return "ok"
                except ProtocolException as e: return "protoexc"
                except asyncio.TimeoutError: return "HANG(sid=%s)" % tab.session_id
            async def close():
                await asyncio.sleep(0)
                await browser.connection.send(cdp.target.close_target(tid))
            r, _ = await asyncio.gather(ev(), close())
            res[r] = res.get(r, 0) + 1
        print(res)
    finally:
        await browser.stop()
asyncio.run(asyncio.wait_for(main(), 100))
