import asyncio
import zendriver as zd
from zendriver import cdp

async def main():
    browser = await zd.start(headless=True)
    try:
        tab = await browser.get("about:blank", new_tab=True)
        await tab.evaluate("1")
        old_listener = tab.listener
        # a page that keeps the session busy (console events) and then closes itself
        tab.add_handler(cdp.runtime.ConsoleAPICalled, lambda e: None)
        await tab.evaluate("let n=0; const iv=setInterval(()=>{console.log(n++)}, 20); 0")
        waiter = asyncio.create_task(tab.wait())       # t=None: wait until idle
        await asyncio.sleep(0.3)
        print("waiter done before close?", waiter.done())
        await browser.connection.send(cdp.target.close_target(tab.target_id))
        await asyncio.sleep(0.5)
        print("listener cancelled:", tab.listener.task.cancelled(), "session_id:", tab.session_id)
        try:
            await asyncio.wait_for(asyncio.shield(waiter), 5)
            print("tab.wait() returned")
        except asyncio.TimeoutError:
            print("tab.wait() still pending 5s after the tab closed -> HANG")
            waiter.print_stack()
            waiter.cancel()
    finally:
        await browser.stop()

asyncio.run(asyncio.wait_for(main(), 50))
