import asyncio, json
import zendriver as zd
from zendriver.core.connection import ProtocolException

async def trial(browser, how):
    tab = await browser.get("about:blank", new_tab=True)
    await tab.evaluate("1")
    # record raw order of frames on the browser websocket
    ws = browser.connection.websocket
    orig = ws.recv
    log = []
    async def recv(*a, **k):
        m = await orig(*a, **k)
        d = json.loads(m)
        log.append((d.get("id"), d.get("method"), "result" in d, (d.get("sessionId") or "")[:6]))
        return m
    ws.recv = recv
    try:
        if how == "page.close":
            r = await asyncio.wait_for(tab.send(zd.cdp.page.close()), 10)
        else:
            r = await asyncio.wait_for(tab.send(zd.cdp.target.close_target(tab.target_id)), 10)
        out = ("ok", r)
    except ProtocolException as e:
        out = ("ProtocolException", str(e).splitlines()[0])
    except asyncio.TimeoutError:
        out = ("HUNG",)
    await asyncio.sleep(0.5)
    ws.recv = orig
    return out, log

async def main():
    browser = await zd.start(headless=True)
    try:
        for how in ("page.close", "target.close"):
            for i in range(3):
                out, log = await trial(browser, how)
                print(how, i, out, log)
    finally:
        await browser.stop()

asyncio.run(main())
