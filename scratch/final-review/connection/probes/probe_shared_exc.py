import asyncio, sys, logging
import zendriver as zd
from zendriver import cdp
from fakews import FakeWS, use, tab_for
print(sys.version.split()[0], zd.__file__)
async def main():
    def script(cmd):
        if cmd.get("sessionId") and cmd["method"].startswith("Runtime."):
            return []  # never answered
        return None
    ws = FakeWS(results={"Target.attachToTarget": {"sessionId": "S1"}}, script=script)
    use(ws)
    bc = zd.core.connection.Connection("ws://fake/devtools/browser/x")
    tab = tab_for(bc)
    await tab.send(cdp.page.bring_to_front())
    t1 = asyncio.ensure_future(tab.send(cdp.runtime.evaluate("a")))
    t2 = asyncio.ensure_future(tab.send(cdp.runtime.evaluate("b")))
    await asyncio.sleep(0.05)
    await tab.aclose()
    r = await asyncio.gather(t1, t2, return_exceptions=True)
    print("same object:", r[0] is r[1])
    print(repr(str(r[0])))
    await bc.aclose()
asyncio.run(main())
