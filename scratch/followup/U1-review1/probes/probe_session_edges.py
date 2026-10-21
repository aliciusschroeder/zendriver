"""flat-session edge cases for the U1 fix (browser-free, uses the reviewers' fakews)"""

import asyncio
import gc
import logging
import sys

import zendriver as zd
from zendriver import cdp
from fakews import FakeWS, tab_for, use
from zendriver.core.connection import Connection

unhandled = []


async def t1_stand_in_failed_by_receive_error():
    """a cancelled, written Network.enable on a session; then a receive error on
    the browser reader. the sentinel must fail the stand-in, so the domain is
    enabled again on the next send"""
    state = {"stall": True, "inject": False}

    def script(cmd):
        m = cmd["method"]
        if m == "Target.attachToTarget":
            return [{"id": cmd["id"], "result": {"sessionId": "S1"}}]
        if m == "Network.enable" and state["stall"]:
            return []
        if state["inject"] and "sessionId" in cmd:
            state["inject"] = False
            return [RuntimeError("cannot receive")]  # reply never comes
        return None

    ws = FakeWS(script=script)
    use(ws)
    bc = Connection("ws://fake/devtools/browser/x")
    tab = tab_for(bc, "T1")
    tab.add_handler(cdp.network.RequestWillBeSent, lambda e: None)
    try:
        try:
            await asyncio.wait_for(tab.send(cdp.page.bring_to_front()), 0.3)
        except asyncio.TimeoutError:
            pass
        print("t1 after timeout: enabled", [m.__name__ for m in tab.enabled_domains], "mapper", {k: v.method for k, v in tab.mapper.items()})
        state["stall"] = False
        state["inject"] = True
        try:
            await asyncio.wait_for(tab.send(cdp.page.bring_to_front()), 2)
            print("t1 send during error: returned")
        except Exception as e:
            print("t1 send during error:", type(e).__name__, e)
        await asyncio.sleep(0.05)
        print("t1 after error: enabled", [m.__name__ for m in tab.enabled_domains], "mapper", {k: v.method for k, v in tab.mapper.items()})
        await asyncio.wait_for(tab.send(cdp.page.bring_to_front()), 2)
        print("t1 final: enabled", [m.__name__ for m in tab.enabled_domains])
        print("t1 methods:", [c["method"] for c in ws.sent])
    finally:
        await tab.aclose()
        await bc.aclose()


async def t2_close_while_session_send_enables():
    """browser connection closes while a tab send waits for its own domain enable"""

    def script(cmd):
        m = cmd["method"]
        if m == "Target.attachToTarget":
            return [{"id": cmd["id"], "result": {"sessionId": "S1"}}]
        if m == "Network.enable":
            return []
        return None

    ws = FakeWS(script=script)
    use(ws)
    bc = Connection("ws://fake/devtools/browser/x")
    tab = tab_for(bc, "T1")
    await asyncio.wait_for(tab.send(cdp.page.bring_to_front()), 2)
    tab.add_handler(cdp.network.RequestWillBeSent, lambda e: None)
    task = asyncio.ensure_future(tab.send(cdp.page.bring_to_front()))
    await asyncio.sleep(0.05)
    await bc.aclose()
    await asyncio.wait({task}, timeout=2)
    print("t2 send result:", task.done() and (type(task.exception()).__name__, str(task.exception()).splitlines()[0]))
    print("t2 methods:", [c["method"] for c in ws.sent])
    print("t2 tab mapper:", tab.mapper, "bc mapper:", bc.mapper)
    del task


async def t3_receive_error_during_session_enable():
    """the browser reader fails while a tab send waits for its own domain enable.
    the tab command must not be sent afterwards"""
    state = {"inject": 0}

    def script(cmd):
        m = cmd["method"]
        if m == "Target.attachToTarget":
            return [{"id": cmd["id"], "result": {"sessionId": "S1"}}]
        if m == "Network.enable" and state["inject"]:
            state["inject"] -= 1
            if state["inject"]:
                # the enable of aopen's _register_handlers is rejected
                return [
                    {
                        "id": cmd["id"],
                        "sessionId": cmd["sessionId"],
                        "error": {"code": -1, "message": "no"},
                    }
                ]
            return [RuntimeError("cannot receive")]
        return None

    ws = FakeWS(script=script)
    use(ws)
    bc = Connection("ws://fake/devtools/browser/x")
    tab = tab_for(bc, "T1")
    try:
        await asyncio.wait_for(tab.send(cdp.page.bring_to_front()), 2)
        tab.add_handler(cdp.network.RequestWillBeSent, lambda e: None)
        state["inject"] = 2
        try:
            await asyncio.wait_for(tab.send(cdp.runtime.evaluate("1")), 2)
            print("t3: returned")
        except Exception as e:
            print("t3:", type(e).__name__, e)
        print("t3 methods:", [c["method"] for c in ws.sent])
    finally:
        await tab.aclose()
        await bc.aclose()


async def main():
    print(sys.version.split()[0], zd.__file__)
    loop = asyncio.get_running_loop()
    loop.set_exception_handler(lambda l, c: unhandled.append(c["message"] + " :: " + repr(c.get("future") or c.get("exception"))[:100]))
    for t in (t1_stand_in_failed_by_receive_error, t2_close_while_session_send_enables, t3_receive_error_during_session_enable):
        await t()
        gc.collect()
        await asyncio.sleep(0.05)
        gc.collect()
        print(f"  {t.__name__} unhandled: {unhandled}")
        unhandled.clear()


logging.basicConfig(level=logging.CRITICAL)
asyncio.run(main())
