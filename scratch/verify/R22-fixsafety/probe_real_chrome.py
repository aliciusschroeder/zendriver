"""real chromium: (1) reply shape for a command on an unknown session, (2) orphan sessions after a timed out first command"""

import asyncio
import json
import sys

import websockets

import zendriver
from zendriver import cdp

print("zendriver:", zendriver.__file__, "python:", sys.version.split()[0])


async def main() -> None:
    browser = await zendriver.start(headless=True)
    try:
        # (1) a second raw client on the browser endpoint
        async with websockets.connect(browser.websocket_url, max_size=2**28) as raw:
            await raw.send(json.dumps({"id": 1, "method": "Runtime.evaluate",
                                       "params": {"expression": "1"}, "sessionId": "0123456789ABCDEF0123456789ABCDEF"}))
            print("unknown session reply:", await asyncio.wait_for(raw.recv(), 5))
            # does an explicit attachToTarget emit Target.attachedToTarget before the reply?
            targets = json.loads(await asyncio.wait_for(
                (await raw.send(json.dumps({"id": 2, "method": "Target.getTargets"}))) or raw.recv(), 5))
            page = next(t for t in targets["result"]["targetInfos"] if t["type"] == "page")
            await raw.send(json.dumps({"id": 3, "method": "Target.attachToTarget",
                                       "params": {"targetId": page["targetId"], "flatten": True}}))
            order = []
            while True:
                m = json.loads(await asyncio.wait_for(raw.recv(), 5))
                order.append(m.get("method") or f"reply id={m.get('id')}")
                if m.get("id") == 3:
                    break
            print("explicit attach message order:", order)

        # (2) orphan sessions
        attached: list[str] = []
        detached: list[str] = []
        browser.connection.add_handler(cdp.target.AttachedToTarget, lambda e: attached.append(e.session_id))
        browser.connection.add_handler(cdp.target.DetachedFromTarget, lambda e: detached.append(e.session_id))
        timeouts = [0.001, 0.003, 0.005, 0.01, 0.02]
        for t in timeouts:
            tab = await browser.get("about:blank", new_tab=True)
            before = len(attached)
            try:
                await asyncio.wait_for(tab.evaluate("1+1"), t)
                outcome = "completed"
            except asyncio.TimeoutError:
                outcome = "timed out"
            await asyncio.sleep(0.3)
            assert await asyncio.wait_for(tab.evaluate("1+1"), 10) == 2
            await asyncio.wait_for(tab.aclose(), 10)
            await asyncio.sleep(0.3)
            mine = attached[before:]
            orphans = [s for s in mine if s not in detached]
            print(f"timeout={t}: first evaluate {outcome}; sessions attached={len(mine)} orphaned={len(orphans)}")
            await browser.connection.send(cdp.target.close_target(tab.target_id))
    finally:
        await browser.stop()


asyncio.run(asyncio.wait_for(main(), 100))
