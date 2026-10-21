import asyncio, sys
sys.path.insert(0, sys.argv[1])
from test_r18_prepare import FakeBrowserSocket, _make_tab
import zendriver as zd
print("zendriver from", zd.__file__)

class MP:
    def setattr(self, obj, name, val): setattr(obj, name, val)

async def main():
    sock = FakeBrowserSocket(delayed=frozenset({"Page.addScriptToEvaluateOnNewDocument"}))
    bc, tab = _make_tab(MP(), sock, expert=True, headless=False)
    try:
        # the first send of the tab times out while its expert script is in flight
        try:
            await asyncio.wait_for(tab.send(zd.cdp.runtime.evaluate("1")), 0.01)
        except asyncio.TimeoutError:
            print("first send timed out")
        await asyncio.wait_for(tab.send(zd.cdp.runtime.evaluate("2")), 5)
        print("addScriptToEvaluateOnNewDocument on S1:", sock.calls_of("Page.addScriptToEvaluateOnNewDocument", "S1"))
    finally:
        await tab.aclose(); await bc.aclose()
asyncio.run(main())
