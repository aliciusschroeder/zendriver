import asyncio, sys
sys.path.insert(0, sys.argv[1])
from test_r18_prepare import FakeBrowserSocket, _make_tab
import zendriver as zd
print("zendriver from", zd.__file__)
class MP:
    def setattr(self, obj, name, val): setattr(obj, name, val)
async def main():
    sock = FakeBrowserSocket(detach_on=frozenset({"Page.addScriptToEvaluateOnNewDocument"}))
    bc, tab = _make_tab(MP(), sock, expert=True, headless=False)
    try:
        try:
            await asyncio.wait_for(tab.send(zd.cdp.runtime.evaluate("1")), 5)
        except Exception as e:
            print("first send raised", repr(e)[:90])
        await asyncio.wait_for(tab.send(zd.cdp.runtime.evaluate("2")), 5)
        print("expert script on S2:", sock.calls_of("Page.addScriptToEvaluateOnNewDocument", "S2"))
    finally:
        await tab.aclose(); await bc.aclose()
asyncio.run(main())
