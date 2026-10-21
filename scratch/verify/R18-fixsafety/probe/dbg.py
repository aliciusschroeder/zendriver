import asyncio, sys, logging
sys.path.insert(0, sys.argv[1])
import pytest
from test_r18_prepare import FakeBrowserSocket, _make_tab
import zendriver as zd
print(zd.__file__)

class MP:
    def setattr(self, obj, name, val): setattr(obj, name, val)

async def main():
    sock = FakeBrowserSocket(delayed=frozenset({"Page.addScriptToEvaluateOnNewDocument"}))
    bc, tab = _make_tab(MP(), sock, expert=True, headless=False)
    t = asyncio.ensure_future(tab.send(zd.cdp.runtime.evaluate("1")))
    await asyncio.sleep(1)
    print("calls", sock.calls)
    print("bc listener", bc.listener, bc.listener.task)
    print("tab listener", tab.listener, tab.listener and tab.listener.task)
    print("tab mapper", tab.mapper, "inbox", tab._inbox and tab._inbox.qsize())
    t.print_stack()
    t.cancel()
asyncio.run(main())
