import asyncio, time
import zendriver as zd
from zendriver import cdp

async def main():
    b = await zd.start(headless=True, autodiscover_targets=False)
    try:
        first = b.tabs[0]
        second_id = await b.connection.send(cdp.target.create_target("about:blank"))
        await b.update_targets()
        # close the first tab through CDP directly (Tab.close would wait 10 s for an event that never comes)
        await b.connection.send(cdp.target.close_target(first.target_id))
        await asyncio.sleep(0.5)
        await b.update_targets()
        live = [t.target_id for t in await b.connection.send(cdp.target.get_targets())]
        print("chrome's live targets:", live)
        print("browser.tabs:", [t.target_id for t in b.tabs])
        print("main_tab is closed first tab:", b.main_tab is first)
        t = time.time()
        try:
            await b.get("data:text/html,hello", timeout=3)
        except BaseException as e:
            print(f"browser.get -> {type(e).__name__} after {time.time()-t:.2f}s: {str(e).splitlines()[0][:120]}")
    finally:
        await b.stop()
asyncio.run(main())
