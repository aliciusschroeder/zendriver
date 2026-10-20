"""Phase A: verify Chrome behaviour with real headless Chromium.

Which CDP commands get an answer while an alert() is open / while the main
thread spins?  Does headless auto-dismiss dialogs?
"""
import asyncio
import sys
import time

import zendriver
from zendriver import cdp

print("zendriver from", zendriver.__file__, "python", sys.version.split()[0])

PAGE = "data:text/html,<p id='topp'>hello world</p><button id='b' onclick=\"alert('clicked')\">b</button>"


async def try_send(tab, name, cmd, t=4.0):
    t0 = time.monotonic()
    try:
        r = await asyncio.wait_for(tab.send(cmd), t)
        print(f"   {name}: ANSWERED in {time.monotonic()-t0:.2f}s -> {str(r)[:60]!r}")
        return True
    except asyncio.TimeoutError:
        print(f"   {name}: NO ANSWER within {t}s")
        return False
    except Exception as e:  # noqa
        print(f"   {name}: error {type(e).__name__}: {str(e)[:80]}")
        return True


async def main():
    browser = await zendriver.start(headless=True)
    try:
        tab = browser.main_tab
        events = []
        tab.add_handler(cdp.page.JavascriptDialogOpening, lambda e: events.append(e))
        await tab.send(cdp.page.enable())
        await tab.get(PAGE)
        print("A1: open alert via setTimeout, wait 1s")
        await tab.evaluate("setTimeout(()=>alert('x'),200)")
        await asyncio.sleep(1.0)
        print("   dialog events:", [e.message for e in events])
        await try_send(tab, "Target.getTargetInfo", cdp.target.get_target_info(tab.target_id))
        await try_send(tab, "DOM.getDocument", cdp.dom.get_document(-1, True))
        await try_send(tab, "DOM.enable", cdp.dom.enable())
        await try_send(tab, "Runtime.evaluate", cdp.runtime.evaluate("1+1"))
        print("A2: still open after 30s more? (does headless auto-dismiss?)")
        await asyncio.sleep(30)
        await try_send(tab, "DOM.getDocument (again, after 34s)", cdp.dom.get_document(-1, True), 4)
        print("A3: dismiss dialog")
        await try_send(tab, "Page.handleJavaScriptDialog", cdp.page.handle_java_script_dialog(True))
        await asyncio.sleep(0.5)
        await try_send(tab, "DOM.getDocument after dismiss", cdp.dom.get_document(-1, True))

        print("A4: busy loop 6s: how long does DOM.getDocument take?")
        await tab.evaluate("setTimeout(()=>{const e=Date.now()+6000; while(Date.now()<e){}},100)")
        await asyncio.sleep(0.5)
        t0 = time.monotonic()
        await asyncio.wait_for(tab.send(cdp.dom.get_document(-1, True)), 20)
        print(f"   getDocument during 6s busy loop answered after {time.monotonic()-t0:.2f}s")
        await asyncio.sleep(1)
        t0 = time.monotonic()
        await try_send(tab, "Target.getTargetInfo idle", cdp.target.get_target_info(tab.target_id))
        await tab.evaluate("setTimeout(()=>{const e=Date.now()+4000; while(Date.now()<e){}},100)")
        await asyncio.sleep(0.5)
        await try_send(tab, "Target.getTargetInfo during busy", cdp.target.get_target_info(tab.target_id), 2)
        await asyncio.sleep(5)

        print("A5: realism: element.click() on a button whose handler calls alert()")
        events.clear()
        btn = await tab.select("#b", timeout=2)
        t0 = time.monotonic()
        try:
            await asyncio.wait_for(btn.click(), 5)
            print(f"   click() returned in {time.monotonic()-t0:.2f}s; dialog events {len(events)}")
        except asyncio.TimeoutError:
            print(f"   click() HUNG (outer 5s); dialog events {len(events)}")
        await try_send(tab, "Page.handleJavaScriptDialog", cdp.page.handle_java_script_dialog(True))
        await asyncio.sleep(0.5)

        print("A6: realism: mouse_click() on the same button")
        events.clear()
        btn = await tab.select("#b", timeout=2)
        t0 = time.monotonic()
        try:
            await asyncio.wait_for(btn.mouse_click(), 5)
            print(f"   mouse_click() returned in {time.monotonic()-t0:.2f}s; dialog events {len(events)}")
        except asyncio.TimeoutError:
            print(f"   mouse_click() HUNG (outer 5s); dialog events {len(events)}")
        await asyncio.sleep(0.5)
        await try_send(tab, "DOM.getDocument with click-alert open", cdp.dom.get_document(-1, True), 3)
        await try_send(tab, "Page.handleJavaScriptDialog", cdp.page.handle_java_script_dialog(True))
        await asyncio.sleep(0.5)

        print("A7: realism: tab.get() of a page with an inline alert() on load")
        events.clear()
        t0 = time.monotonic()
        try:
            await asyncio.wait_for(tab.get("data:text/html,<p>x</p><script>alert('onload')</script>"), 20)
            print(f"   tab.get returned in {time.monotonic()-t0:.2f}s; dialog events {len(events)}")
        except asyncio.TimeoutError:
            print(f"   tab.get HUNG (outer 20s); dialog events {len(events)}")
        await try_send(tab, "DOM.getDocument after get", cdp.dom.get_document(-1, True), 3)
        await try_send(tab, "Page.handleJavaScriptDialog", cdp.page.handle_java_script_dialog(True))
    finally:
        await browser.stop()


asyncio.run(main())
