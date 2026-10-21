import asyncio, time, sys
import zendriver as zd
from zendriver import cdp
import srv
print("zendriver from", zd.__file__, "python", sys.version.split()[0])

def last(path):
    for p, ua, ch in reversed(srv.UA_LOG):
        if p == path:
            return ("HeadlessChrome" in (ua or ""), ua, ch)

async def main(expert):
    srv.UA_LOG.clear()
    s, B = srv.start()
    b = await zd.start(headless=True, expert=expert)
    try:
        print(f"--- expert={expert}")
        t = await b.get(B + "/main-tab")
        await asyncio.sleep(0.3)
        print("/main-tab  server HeadlessChrome:", last("/main-tab")[0], "| js ua headless:", "Headless" in await t.evaluate("window.__ua"), "| shadow open:", await t.evaluate("window.__shadow"))
        t2 = await b.get(B + "/new-tab", new_tab=True)
        await asyncio.sleep(0.5)
        print("/new-tab   server HeadlessChrome:", last("/new-tab")[0], "| js ua headless:", "Headless" in await t2.evaluate("window.__ua"), "| shadow open:", await t2.evaluate("window.__shadow"))
        await t2.reload()
        await asyncio.sleep(0.5)
        print("/new-tab (after reload) server HeadlessChrome:", last("/new-tab")[0], "| js ua headless:", "Headless" in await t2.evaluate("window.__ua"), "| shadow open:", await t2.evaluate("window.__shadow"))
        t3 = await b.create_context(B + "/ctx")
        await asyncio.sleep(1.0)
        print("/ctx       server HeadlessChrome:", last("/ctx") and last("/ctx")[0], "| js ua headless:", "Headless" in await t3.evaluate("window.__ua"))
        # popup via window.open from main tab
        await t.evaluate(f"window.open('{B}/popup', '_blank'); 1")
        await asyncio.sleep(1.0)
        print("/popup     server HeadlessChrome:", last("/popup") and last("/popup")[0])
        print("main-tab UA sample:", last("/main-tab")[1])
        print("new-tab  UA sample:", [ua for p, ua, ch in srv.UA_LOG if p == "/new-tab"][0])
    finally:
        await b.stop()
        s.shutdown()

asyncio.run(main(False))
asyncio.run(main(True))
