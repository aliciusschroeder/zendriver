"""B14.7 against real headless chromium.

(a) what chrome answers to a command on an unknown session (raw second client)
(b) attach racing a close: first tab.send attaches while the target is being closed and the
    event loop is busy for a moment (frames pile up in the socket and are read in one burst)
"""

import asyncio
import json
import sys
import time

import websockets

import zendriver
from zendriver import cdp

print("python", sys.version.split()[0], "zendriver from", zendriver.__file__)


async def raw_unknown_session(browser):
    url = browser.connection.websocket_url
    async with websockets.connect(url, max_size=2**24) as ws:
        await ws.send(
            json.dumps(
                {
                    "id": 1,
                    "sessionId": "0123456789ABCDEF0123456789ABCDEF",
                    "method": "Runtime.evaluate",
                    "params": {"expression": "1"},
                }
            )
        )
        print("(a) chrome reply to unknown session:", await asyncio.wait_for(ws.recv(), 5))


async def race_once(browser, block):
    tab = await browser.get("about:blank", new_tab=True)
    tid = tab.target_id
    assert tab.session_id is None
    t = asyncio.ensure_future(tab.send(cdp.runtime.evaluate("1")))
    await asyncio.sleep(0)  # attachToTarget written to the socket
    c = asyncio.ensure_future(
        browser.connection.send(cdp.target.close_target(target_id=tid))
    )
    await asyncio.sleep(0)  # closeTarget written right behind it
    if block:
        time.sleep(block)  # event loop busy: chrome's frames accumulate in the socket
    done, _ = await asyncio.wait({t}, timeout=5)
    try:
        await asyncio.wait_for(c, 5)
    except Exception:
        pass
    if not done:
        print(
            f"  block={block}: HANG; tab.session_id={tab.session_id} "
            f"registered={list(browser.connection._sessions)} tab.mapper={list(tab.mapper)} "
            f"browser mapper={list(browser.connection.mapper)}"
        )
        t.print_stack(file=sys.stdout)
        t.cancel()
        try:
            await t
        except BaseException:
            pass
        # a later send on the same tab
        t2 = asyncio.ensure_future(tab.send(cdp.runtime.evaluate("2")))
        done2, _ = await asyncio.wait({t2}, timeout=3)
        print("  later send on the same tab:", "HANG" if not done2 else repr(t2.exception() or t2.result()))
        if not done2:
            t2.cancel()
            try:
                await t2
            except BaseException:
                pass
        return "hang"
    exc = t.exception()
    return "ok" if exc is None else type(exc).__name__ + ":" + str(exc).splitlines()[0]


async def main():
    browser = await zendriver.start(headless=True)
    try:
        await raw_unknown_session(browser)
        for block in (0, 0.2):
            results = []
            for i in range(8):
                results.append(await race_once(browser, block))
            print(f"(b) block={block}: results={results}")
    finally:
        await browser.stop()


asyncio.run(main())
