"""A1.5 against real headless chromium: a session command whose reply is read in the same
burst as Target.detachedFromTarget. Two triggers:
  (1) Page.close sent through the tab's own session (chrome answers it, then detaches)
  (2) a plain Runtime.evaluate racing a Target.closeTarget sent on the browser connection
In both, the event loop is optionally busy for `block` seconds right after the writes, so
chrome's frames pile up in the socket and are read together.
"""

import asyncio
import json
import sys
import time

import zendriver
from zendriver import cdp
from zendriver.core.connection import ProtocolException

print("python", sys.version.split()[0], "zendriver from", zendriver.__file__)


async def trial(browser, mode, block):
    tab = await browser.get("about:blank", new_tab=True)
    await tab.evaluate("1")  # attach the session first
    tid = tab.target_id
    sid = tab.session_id
    raw = []
    ws = browser.connection.websocket
    orig_recv = ws.recv

    async def recv(*a, **k):
        data = await orig_recv(*a, **k)
        raw.append(json.loads(data))
        return data

    ws.recv = recv

    if mode == "page.close":
        t = asyncio.ensure_future(tab.send(cdp.page.close()))
        await asyncio.sleep(0)
    else:
        t = asyncio.ensure_future(tab.send(cdp.runtime.evaluate("1+1")))
        await asyncio.sleep(0)
        asyncio.ensure_future(browser.connection.send(cdp.target.close_target(tid)))
        await asyncio.sleep(0)
    if block:
        time.sleep(block)
    done, _ = await asyncio.wait({t}, timeout=5)
    if not done:
        t.cancel()
        return "hang"
    exc = t.exception()
    ws.recv = orig_recv
    if exc is not None and not trial.shown:
        trial.shown = True
        rel = [m for m in raw if m.get("sessionId") == sid or m.get("params", {}).get("sessionId") == sid]
        print("   frames for session", sid, "read by the browser listener:")
        for m in rel:
            print("     ", json.dumps(m)[:160])
    # give the close time to finish before the next trial
    await asyncio.sleep(0.2)
    return "ok" if exc is None else "PE:" + str(exc).splitlines()[0]


trial.shown = False


async def main():
    browser = await zendriver.start(headless=True)
    try:
        for mode in ("page.close", "evaluate+closeTarget"):
            trial.shown = False
            for block in (0, 0.2):
                res = [await trial(browser, mode, block) for _ in range(6)]
                print(f"mode={mode} block={block}: {res}")
    finally:
        await browser.stop()


asyncio.run(main())
