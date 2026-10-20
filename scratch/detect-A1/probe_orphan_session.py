import asyncio
import zendriver as zd

async def main():
    browser = await zd.start(headless=True)
    try:
        attached = []
        detached = []
        browser.connection.add_handler(zd.cdp.target.AttachedToTarget, lambda e: attached.append(e.session_id))
        browser.connection.add_handler(zd.cdp.target.DetachedFromTarget, lambda e: detached.append(e.session_id))
        tab = await browser.get("about:blank", new_tab=True)
        print("tab session before:", tab.session_id)
        try:
            await asyncio.wait_for(tab.evaluate("1 + 1"), 0.002)
        except asyncio.TimeoutError:
            print("evaluate timed out")
        await asyncio.sleep(0.5)
        print("tab session after timeout:", tab.session_id, "attached events so far:", attached)
        print(await tab.evaluate("1 + 1"), "tab session now:", tab.session_id)
        await asyncio.sleep(0.2)
        print("attached:", attached)
        await tab.aclose()
        await asyncio.sleep(0.5)
        print("detached after tab.aclose():", detached)
        print("orphan sessions (attached, never detached):", [s for s in attached if s not in detached])
    finally:
        await browser.stop()

asyncio.run(main())
