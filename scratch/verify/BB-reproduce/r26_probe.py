import asyncio, sys, os
sys.path.insert(0, os.path.dirname(__file__))
import zendriver as zd
from zendriver import cdp
from common import start_server
print("zendriver from", zd.__file__, "python", sys.version.split()[0])

def spy(tab, log):
    orig = tab._send_transaction
    async def wrapped(tx):
        log.append((tx.method, tx.params))
        return await orig(tx)
    tab._send_transaction = wrapped
    return orig

async def stuck(coro, t, label):
    task = asyncio.ensure_future(coro)
    done, _ = await asyncio.wait({task}, timeout=t)
    if done:
        try:
            r = task.result()
            print(f"[{label}] completed: {r!r}"[:300])
        except BaseException as e:
            print(f"[{label}] raised {type(e).__name__}: {e}"[:300])
        return True
    print(f"[{label}] STILL PENDING after {t}s; stack:")
    task.print_stack(file=sys.stdout)
    task.cancel()
    try:
        await task
    except BaseException:
        pass
    return False

async def scenario_a22(browser, base, with_handler):
    print(f"\n=== A2.2 manual disable then navigate (handler={with_handler})")
    tab = browser.main_tab
    await tab.get(base + "/a")
    paused = []
    def h(ev):
        paused.append(ev.request.url)
    if with_handler:
        tab.add_handler(cdp.fetch.RequestPaused, h)
    await tab.send(cdp.fetch.enable(patterns=[cdp.fetch.RequestPattern(url_pattern="*/x")]))
    print("after enable: enabled", [m.__name__ for m in tab.enabled_domains], "manual", [m.__name__ for m in tab.manually_enabled_domains])
    await tab.send(cdp.fetch.disable())
    print("after disable: enabled", [m.__name__ for m in tab.enabled_domains], "manual", [m.__name__ for m in tab.manually_enabled_domains])
    log = []
    orig = spy(tab, log)
    ok = await stuck(tab.send(cdp.page.navigate(base + "/b")), 5, "navigate")
    tab._send_transaction = orig
    print("sent during navigate:", log)
    print("paused requests:", paused)
    # cleanup
    tab.remove_handlers()
    await asyncio.wait_for(tab.send(cdp.fetch.disable()), 10)
    await asyncio.sleep(0.5)
    return ok

async def scenario_a22_intercept(browser, base):
    print("\n=== A2.2 variant: user RequestPaused handler + tab.intercept()")
    tab = browser.main_tab
    await tab.get(base + "/a")
    paused = []
    tab.add_handler(cdp.fetch.RequestPaused, lambda ev: paused.append(ev.request.url))
    from zendriver.cdp.fetch import RequestStage
    from zendriver.cdp.network import ResourceType
    async with tab.intercept("*/never", RequestStage.REQUEST, ResourceType.XHR) as it:
        pass
    print("after intercept exit: enabled", [m.__name__ for m in tab.enabled_domains], "manual", [m.__name__ for m in tab.manually_enabled_domains])
    log = []
    orig = spy(tab, log)
    ok = await stuck(tab.send(cdp.page.navigate(base + "/b2")), 5, "navigate")
    tab._send_transaction = orig
    print("sent during navigate:", log)
    print("paused requests:", paused)
    tab.remove_handlers()
    await asyncio.wait_for(tab.send(cdp.fetch.disable()), 10)
    await asyncio.sleep(0.5)

async def scenario_a122(browser, base):
    print("\n=== A12.2 remove_handlers leaves Fetch enabled")
    tab = browser.main_tab
    await tab.get(base + "/a")
    paused = []
    async def h(ev):
        paused.append(ev.request.url)
        await tab.send(cdp.fetch.continue_request(request_id=ev.request_id))
    tab.add_handler(cdp.fetch.RequestPaused, h)
    ok = await stuck(tab.get(base + "/c"), 10, "first get with handler")
    print("with handler: paused", paused, "enabled", [m.__name__ for m in tab.enabled_domains])
    tab.remove_handlers(cdp.fetch.RequestPaused, h)
    paused.clear()
    log = []
    orig = spy(tab, log)
    ok2 = await stuck(tab.get(base + "/d", timeout=5), 15, "second get after remove")
    tab._send_transaction = orig
    print("sent during second get:", log)
    print("after remove: enabled", [m.__name__ for m in tab.enabled_domains], "manual", [m.__name__ for m in tab.manually_enabled_domains], "handlers", dict(tab.handlers))
    ok3 = await stuck(tab.evaluate("1+1"), 5, "evaluate after")
    # see whether browser really has fetch enabled: check a fresh paused event count via handler
    seen = []
    tab.add_handler(cdp.fetch.RequestPaused, lambda ev: seen.append(ev.request.url))
    # don't send anything (would re-enable), just wait for events from the pending nav (already paused)
    await asyncio.sleep(1)
    print("RequestPaused events seen after re-adding a passive handler (no send):", seen)
    tab.remove_handlers()
    await asyncio.wait_for(tab.send(cdp.fetch.disable()), 10)
    await asyncio.sleep(0.5)
    ok4 = await stuck(tab.get(base + "/e", timeout=5), 15, "get after explicit Fetch.disable")

async def main():
    srv, base = start_server()
    browser = await zd.start(headless=True)
    try:
        await scenario_a22(browser, base, with_handler=False)
        await scenario_a22(browser, base, with_handler=True)
        await scenario_a22_intercept(browser, base)
        await scenario_a122(browser, base)
    finally:
        await browser.stop()
        srv.shutdown()

asyncio.run(main())
