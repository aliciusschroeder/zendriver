"""Q12: a manual X.enable() send cancelled inside send()'s own _register_handlers
leaves X in manually_enabled_domains although X.enable never reached the browser;
_register_handlers then never auto-enables X for X's event handlers."""
import asyncio, sys, logging
import zendriver as zd
from zendriver import cdp
from fakews import FakeWS, use, tab_for
print(sys.version.split()[0], zd.__file__)

async def main():
    st = {"stall": False, "stalled": asyncio.Event()}
    def script(cmd):
        if cmd["method"] == "CSS.enable":
            # fails like chrome's "DOM agent needs to be enabled first"; the second
            # one (send()'s own _register_handlers) is slow this time
            if st["stall"] and st["n"] == 1:
                st["stalled"].set(); return []
            st["n"] = st.get("n", 0) + 1
            return [{"id": cmd["id"], "sessionId": cmd.get("sessionId"), "error": {"code": -32000, "message": "DOM agent needs to be enabled first."}}]
        return None
    ws = FakeWS(results={"Target.attachToTarget": {"sessionId": "S1"}}, script=script)
    use(ws)
    bc = zd.core.connection.Connection("ws://fake/devtools/browser/x")
    tab = tab_for(bc)
    await tab.send(cdp.page.bring_to_front())
    tab.add_handler(cdp.css.StyleSheetAdded, lambda e: None)
    st["n"] = 0; st["stall"] = True
    t = asyncio.ensure_future(tab.send(cdp.overlay.enable()))   # manual enable, as Element.flash does
    await asyncio.wait_for(st["stalled"].wait(), 2)
    t.cancel()
    await asyncio.wait({t}, timeout=2)
    print("manual send cancelled:", t.cancelled(), "" if t.cancelled() or not t.done() else t.exception())
    st["stall"] = False
    print("Overlay.enable sent before the cancel:", any(c["method"] == "Overlay.enable" for c in ws.sent))
    # the user now listens for an Overlay event
    tab.add_handler(cdp.overlay.InspectNodeRequested, lambda e: None)
    ws.sent.clear()
    for _ in range(3):
        await asyncio.wait_for(tab.send(cdp.page.bring_to_front()), 2)
    print("Overlay.enable ever sent:", any(c["method"] == "Overlay.enable" for c in ws.sent) )
    print("manually_enabled_domains:", [m.__name__ for m in tab.manually_enabled_domains])
    print("enabled_domains:", [m.__name__ for m in tab.enabled_domains])
    await tab.aclose(); await bc.aclose()
logging.basicConfig(level=logging.CRITICAL)
asyncio.run(main())
