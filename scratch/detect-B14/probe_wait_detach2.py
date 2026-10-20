import asyncio, sys
import zendriver as zd
from zendriver import cdp

async def main(close):
    browser = await zd.start(headless=True)
    try:
        tab = await browser.get("about:blank", new_tab=True)
        tab.add_handler(cdp.runtime.ConsoleAPICalled, lambda e: None)
        # page is busy for ~1s (console events every 20ms), then goes quiet
        await tab.evaluate("let n=0; const iv=setInterval(()=>{console.log(n++); if(n>50) clearInterval(iv)}, 20); 0")
        loop = asyncio.get_running_loop(); t0 = loop.time()
        waiter = asyncio.create_task(tab.wait())       # documented: waits until listener reports idle
        await asyncio.sleep(0.3)
        if close:
            await browser.connection.send(cdp.target.close_target(tab.target_id))
        try:
            await asyncio.wait_for(asyncio.shield(waiter), 8)
            print(f"close={close}: tab.wait() returned after {loop.time()-t0:.2f}s")
        except asyncio.TimeoutError:
            print(f"close={close}: tab.wait() still pending after {loop.time()-t0:.2f}s -> HANG (listener done={tab.listener.task.done()}, session_id={tab.session_id})")
            waiter.cancel()
    finally:
        await browser.stop()

asyncio.run(asyncio.wait_for(main(sys.argv[1]=="1"), 50))
