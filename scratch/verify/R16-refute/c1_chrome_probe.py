"""SEED-C1 with real Chromium: provoke a client-side 1009 close (message too big) while Chrome stays alive."""
import asyncio, sys
import zendriver
import zendriver.core.connection as zc
from zendriver import cdp
from zendriver.core.connection import Connection
print("zendriver from", zendriver.__file__, "python", sys.version.split()[0])

async def main():
    zc.MAX_SIZE = 200_000  # module global read by aopen at connect time
    browser = await zendriver.start(headless=True)
    try:
        tab = await browser.get("data:text/html,<p>x</p>")
        try:
            await asyncio.wait_for(tab.evaluate("'x'.repeat(300000)"), 10)
        except Exception as e:
            print("big evaluate raised:", type(e).__name__, str(e)[:100])
        await asyncio.sleep(0.3)
        bc = browser.connection
        print("browser listener running:", bc.listener.running, " websocket None:", bc.websocket is None, " closed:", bc.closed)
        for i in range(2):
            try:
                await asyncio.wait_for(bc.send(cdp.browser.get_version()), 10)
                print("browser send ok")
            except asyncio.TimeoutError:
                print("browser send HANG")
            except Exception as e:
                print(f"browser send #{i} raised", type(e).__name__, str(e)[:80])
        try:
            print("tab.evaluate ->", await asyncio.wait_for(tab.evaluate("1+1"), 10))
        except Exception as e:
            print("tab.evaluate raised", type(e).__name__, str(e)[:80])
        print("chrome process alive:", browser._process.poll() is None)
        fresh = Connection(bc.websocket_url)
        try:
            v = await asyncio.wait_for(fresh.send(cdp.browser.get_version()), 10)
            print("fresh Connection to same URL works (Chrome accepts reconnect): product =", v[1])
        finally:
            await fresh.aclose()
        # what a reset would enable
        bc.websocket = None
        try:
            await asyncio.wait_for(bc.send(cdp.browser.get_version()), 10)
            print("after manual websocket=None: browser send ok (reconnected)")
            print("after manual reset: tab.evaluate ->", await asyncio.wait_for(tab.evaluate("1+1"), 10))
        except Exception as e:
            print("after manual reset raised", type(e).__name__, str(e)[:100])
    finally:
        await browser.stop()
asyncio.run(main())
