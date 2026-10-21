"""a receive error on a nested domain enable kills the browser reader; the
enclosing send then writes its own enable without a reader. same on base?"""

import asyncio
import logging
import sys

import zendriver as zd
from zendriver import cdp
from fakews import FakeWS, tab_for, use
from zendriver.core.connection import Connection


async def main():
    print(sys.version.split()[0], zd.__file__)
    state = {"inject": False}

    def script(cmd):
        m = cmd["method"]
        if m == "Target.attachToTarget":
            return [{"id": cmd["id"], "result": {"sessionId": "S1"}}]
        if m == "Log.enable" and state["inject"]:
            state["inject"] = False
            return [RuntimeError("cannot receive"), "REPLY"]
        return None

    ws = FakeWS(script=script)
    use(ws)
    bc = Connection("ws://fake/devtools/browser/x")
    tab = tab_for(bc, "T1")
    try:
        await asyncio.wait_for(tab.send(cdp.page.bring_to_front()), 2)
        tab.add_handler(cdp.network.RequestWillBeSent, lambda e: None)
        tab.add_handler(cdp.log.EntryAdded, lambda e: None)
        state["inject"] = True
        try:
            await asyncio.wait_for(tab.send(cdp.page.bring_to_front()), 2)
            print("send: returned")
        except asyncio.TimeoutError:
            print("send: HUNG (2s safety net)")
        except Exception as e:
            print("send:", type(e).__name__, e)
        print("methods:", [c["method"] for c in ws.sent])
        print("bc listener running:", bc.listener.running if bc.listener else None, "unread frames:", ws.frames.qsize())
    finally:
        await tab.aclose()
        await bc.aclose()


logging.basicConfig(level=logging.CRITICAL)
asyncio.run(main())
