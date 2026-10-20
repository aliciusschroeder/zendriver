import asyncio, re, sys, traceback, pathlib
import zendriver as zd
from zendriver import cdp

print("zendriver from", zd.__file__, "python", sys.version.split()[0])
URL = pathlib.Path(__file__).with_name("site").joinpath("index.html").resolve().as_uri()

def names(l):
    return [m.__name__.rsplit(".", 1)[-1] for m in l]

async def scenario_a(browser):
    print("\n=== scenario A: network handler -> evaluate -> remove -> runtime handler -> evaluate ===")
    tab = await browser.get(URL)
    h = lambda e: None
    tab.add_handler(cdp.network.RequestWillBeSent, h)
    print("eval1:", await tab.evaluate("1"))
    print("enabled after eval1:", names(tab.enabled_domains), "manual:", names(tab.manually_enabled_domains))
    tab.remove_handlers(cdp.network.RequestWillBeSent, h)
    got = []
    tab.add_handler(cdp.runtime.ConsoleAPICalled, lambda e: got.append(e))
    try:
        r = await asyncio.wait_for(tab.evaluate("window.__marker = 42; console.log('probe'); 2"), 20)
        print("eval2 OK:", r)
    except Exception as e:
        print("eval2 RAISED:", type(e).__name__, e)
        traceback.print_exc(limit=-4, file=sys.stdout)
    print("enabled after eval2:", names(tab.enabled_domains))
    # was the user's command sent? (verified against chrome)
    print("marker after eval2 (undef means command never reached chrome):",
          await tab.evaluate("window.__marker === undefined ? 'undef' : window.__marker"))
    print("eval3:", await tab.evaluate("3"), "enabled:", names(tab.enabled_domains))
    await tab.evaluate("console.log('after')")
    await asyncio.sleep(0.5)
    print("ConsoleAPICalled events received:", [a.args[0].value for a in got])

async def scenario_b(browser):
    print("\n=== scenario B: expect_request(reload) -> add page.LoadEventFired -> reload ===")
    tab = await browser.get(URL, new_tab=True)
    print("enabled at start:", names(tab.enabled_domains), "manual:", names(tab.manually_enabled_domains))
    async with tab.expect_request(re.compile(".*index.html")) as req:
        await tab.reload()
        ev = await asyncio.wait_for(req.value, 10)
        print("expect_request matched:", ev.request.url[-20:])
    print("enabled after expect:", names(tab.enabled_domains), "handlers:", {k.__name__: len(v) for k, v in tab.handlers.items()})
    loads = []
    tab.add_handler(cdp.page.LoadEventFired, lambda e: loads.append(e))
    try:
        await asyncio.wait_for(tab.reload(), 20)
        print("reload OK")
    except Exception as e:
        print("reload RAISED:", type(e).__name__, e)
        traceback.print_exc(limit=-4, file=sys.stdout)
    print("enabled after reload:", names(tab.enabled_domains))
    await asyncio.sleep(1.5)
    print("LoadEventFired count after failed reload (0 => reload not sent / no load):", len(loads))
    await asyncio.wait_for(tab.reload(), 20)
    await asyncio.sleep(1.5)
    print("LoadEventFired count after a second reload:", len(loads))

async def scenario_c(browser):
    print("\n=== scenario C (control): same but a plain send happens between remove and add ===")
    tab = await browser.get(URL, new_tab=True)
    h = lambda e: None
    tab.add_handler(cdp.network.RequestWillBeSent, h)
    await tab.evaluate("1")
    tab.remove_handlers(cdp.network.RequestWillBeSent, h)
    await tab.evaluate("1.5")
    print("enabled after intermediate send:", names(tab.enabled_domains))
    tab.add_handler(cdp.log.EntryAdded, lambda e: None)
    try:
        print("eval OK:", await asyncio.wait_for(tab.evaluate("2"), 20))
    except Exception as e:
        print("eval RAISED:", type(e).__name__, e)
    print("enabled:", names(tab.enabled_domains))

async def main():
    browser = await zd.start(headless=True)
    try:
        await scenario_a(browser)
        await scenario_b(browser)
        await scenario_c(browser)
    finally:
        await browser.stop()

asyncio.run(asyncio.wait_for(main(), 100))
