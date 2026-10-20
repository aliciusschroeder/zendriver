import asyncio, sys
import zendriver as zd
from zendriver import cdp
from zendriver.core.connection import ProtocolException

async def main(race):
    browser = await zd.start(headless=True)
    try:
        tid = await browser.connection.send(cdp.target.create_target("about:blank"))
        tab = await browser._get_tab(tid)
        async def first_send():
            try:
                await tab.evaluate("1"); return "ok"
            except ProtocolException as e:
                return "ProtocolException: " + str(e).splitlines()[0]
        async def closer():
            while tab.session_id is None:
                await asyncio.sleep(0)
            await tab.aclose()
        if race:
            r, _ = await asyncio.gather(first_send(), closer())
        else:
            r = await first_send(); await tab.aclose()
        print("first send:", r, "| _prep_headless_done after detach:", getattr(tab, "_prep_headless_done", None))
        ua = await tab.evaluate("navigator.userAgent")
        print(f"race={race}: UA after reattach: {ua}")
    finally:
        await browser.stop()
asyncio.run(asyncio.wait_for(main(sys.argv[1] == "1"), 50))
