"""A1.6 on real Chromium: cancel the first command of a fresh tab while Target.attachToTarget
is in flight; check whether Chrome keeps an orphan session alive and for how long."""
import asyncio, json, time, sys
import zendriver
from zendriver import cdp
print("zendriver from", zendriver.__file__, "py", sys.version.split()[0])

async def main():
    browser = await zendriver.start(headless=True)
    bc = browser.connection
    attached, detached = [], []
    bc.add_handler(cdp.target.AttachedToTarget, lambda e: attached.append(str(e.session_id)))
    bc.add_handler(cdp.target.DetachedFromTarget, lambda e: detached.append(str(e.session_id)))
    try:
        # measure attach RTT for context
        rtts = []
        for _ in range(5):
            t = await browser.get("about:blank", new_tab=True)
            t0 = time.perf_counter(); await t.send(cdp.runtime.evaluate("1")); rtts.append((time.perf_counter() - t0) * 1000)
            await t.close()
        print("first-send (attach+prepare+evaluate) ms:", [round(x, 2) for x in rtts])

        tab = await browser.get("about:blank", new_tab=True)
        assert tab.session_id is None
        task = asyncio.create_task(tab.evaluate("1+1"))
        # yield until the attach command is registered in the browser mapper, then a bit more so it is on the wire
        for _ in range(1000):
            await asyncio.sleep(0)
            if any(tx.method == "Target.attachToTarget" for tx in bc.mapper.values()):
                break
        await asyncio.sleep(0)
        task.cancel()
        try: await task
        except asyncio.CancelledError: print("first evaluate cancelled during attach; tab.session_id =", tab.session_id)
        await asyncio.sleep(0.3)
        print("attached so far:", attached)
        print("evaluate again ->", await asyncio.wait_for(tab.evaluate("1+1"), 5), "session", tab.session_id)
        await tab.aclose()
        await asyncio.sleep(0.3)
        orphans = [s for s in attached if s not in detached]
        print("attached:", attached, "\ndetached after tab.aclose():", detached, "\norphans:", orphans)
        # is the orphan session really alive in chrome? send a raw command on it
        for sid in orphans:
            fut = asyncio.get_running_loop().create_future()
            got = []
            ws = bc.websocket; orig = ws.recv
            async def rec(*a, **k):
                m = await orig(*a, **k); d = json.loads(m)
                if d.get("id") == 4242: got.append(d)
                return m
            ws.recv = rec
            await ws.send(json.dumps({"id": 4242, "method": "Runtime.evaluate", "params": {"expression": "6*7", "returnByValue": True}, "sessionId": sid}))
            await asyncio.sleep(0.3)
            ws.recv = orig
            print("raw command on orphan session ->", got)
        await tab.close()
        await asyncio.sleep(0.3)
        print("detached after tab.close():", detached)
    finally:
        await browser.stop()

asyncio.run(main())
