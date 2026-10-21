import asyncio, sys, logging
import zendriver as zd
from zendriver import cdp
from fakews import FakeWS, use, tab_for, listener_tasks
print(sys.version.split()[0], zd.__file__)
TI = {"targetInfo": {"targetId": "T1", "type": "page", "title": "", "url": "about:blank", "attached": True, "canAccessOpener": False}}

async def main():
    st = {"n": 0}
    def script(cmd):
        if cmd["method"] == "Page.bringToFront" and st["n"] == 0:
            st["n"] += 1
            return ["REPLY", RuntimeError("cannot receive")]  # parent dies after this reply
        return None
    ws = FakeWS(results={"Target.attachToTarget": {"sessionId": "S1"}, "Target.getTargetInfo": TI}, script=script)
    use(ws)
    bc = zd.core.connection.Connection("ws://fake/devtools/browser/x")
    tab = tab_for(bc)
    try:
        await asyncio.wait_for(tab.send(cdp.page.bring_to_front()), 2)
    except Exception as e:
        print("first send:", type(e).__name__)
    await asyncio.sleep(0.05)
    print("parent listener running:", bc.listener.running, "tab listener running:", tab.listener.running)
    for name, coro in [("tab.wait()", tab.wait()), ("tab.wait(0.3)", tab.wait(0.3)), ("bc.wait()", bc.wait())]:
        try:
            await asyncio.wait_for(coro, 5); print(name, "returned; parent running:", bc.listener.running)
        except Exception as e:
            print(name, "->", type(e).__name__, e)
    print("live listener tasks:", len(listener_tasks()))
    await tab.aclose(); await bc.aclose()
    await asyncio.sleep(0.2)
    print("live listener tasks after close:", len(listener_tasks()))
logging.basicConfig(level=logging.CRITICAL)
asyncio.run(main())
