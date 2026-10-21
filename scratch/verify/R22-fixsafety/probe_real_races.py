"""real chromium: try to hit A1.5 (page.close through own session) and B14.7 (first send racing close_target)"""

import asyncio
import collections
import sys

import zendriver
from zendriver import cdp
from zendriver.core.connection import ProtocolException

print("zendriver:", zendriver.__file__, "python:", sys.version.split()[0])
N = int(sys.argv[1]) if len(sys.argv) > 1 else 20


async def main() -> None:
    browser = await zendriver.start(headless=True)
    a15: collections.Counter[str] = collections.Counter()
    b147: collections.Counter[str] = collections.Counter()
    try:
        for _ in range(N):
            tab = await browser.get("about:blank", new_tab=True)
            await tab.evaluate("1")  # attach
            try:
                await asyncio.wait_for(tab.send(cdp.page.close()), 5)
                a15["page.close ok"] += 1
            except ProtocolException as e:
                a15["ProtocolException: " + str(e).splitlines()[0]] += 1
            except asyncio.TimeoutError:
                a15["timeout"] += 1
            await asyncio.sleep(0.05)
        for _ in range(N):
            tab = await browser.get("about:blank", new_tab=True)
            close = asyncio.ensure_future(
                browser.connection.send(cdp.target.close_target(tab.target_id))
            )
            try:
                await asyncio.wait_for(tab.send(cdp.runtime.evaluate("1")), 3)
                b147["evaluate ok"] += 1
            except ProtocolException as e:
                b147["ProtocolException: " + str(e).splitlines()[0]] += 1
            except asyncio.TimeoutError:
                b147["HANG (3s timeout)"] += 1
            try:
                await asyncio.wait_for(close, 5)
            except Exception:
                pass
            await tab.aclose()
            await asyncio.sleep(0.05)
    finally:
        await browser.stop()
    print("A1.5 page.close via own session:", dict(a15))
    print("B14.7 first send racing close_target:", dict(b147))


asyncio.run(asyncio.wait_for(main(), 110))
