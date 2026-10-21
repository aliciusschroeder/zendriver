"""B: a tab command whose reply was already routed to the tab inbox is failed
by the parent listener's next receive error (Q1)."""
import asyncio, sys, logging
import zendriver as zd
from fakews import FakeWS, use, tab_for

print(sys.version.split()[0], zd.__file__)

async def main():
    arm = {"on": False}
    def script(cmd):
        if "sessionId" in cmd and arm["on"] and cmd["method"] == "Runtime.evaluate":
            arm["on"] = False
            return ["REPLY", "not json"]  # reply arrives fine, then a bad frame
        return None
    ws = FakeWS(results={"Target.attachToTarget": {"sessionId": "S1"},
                         "Runtime.evaluate": {"result": {"type": "number", "value": 2}}},
                script=script)
    use(ws)
    bc = zd.core.connection.Connection("ws://fake/devtools/browser/x")
    tab = tab_for(bc)
    await asyncio.wait_for(tab.send(zd.cdp.page.bring_to_front()), 2)
    arm["on"] = True
    try:
        r = await asyncio.wait_for(tab.send(zd.cdp.runtime.evaluate("1+1")), 2)
        print("RESULT: send returned", r[0].value)
    except Exception as e:
        print("RESULT: send raised", type(e).__name__, e)
    print("reply frames sent:", [c["method"] for c in ws.sent])
    await tab.aclose(); await bc.aclose()

logging.basicConfig(level=logging.ERROR)
asyncio.run(main())
