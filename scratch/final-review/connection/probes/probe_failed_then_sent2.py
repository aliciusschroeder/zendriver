"""C2: one-shot receive error. browser.connection has a Page handler; Page.enable
is rejected by the browser target (as real chrome does), so every send retries it
in send()'s own _register_handlers while the caller's tx is already in mapper.
A single receive error at that moment fails the caller's command, which is
nevertheless sent afterwards."""
import asyncio, sys, logging
import zendriver as zd
from fakews import FakeWS, use

print(sys.version.split()[0], zd.__file__)

async def main():
    state = {"armed": False, "page_enables": 0}
    def script(cmd):
        if cmd["method"] == "Page.enable":
            state["page_enables"] += 1
            if state["armed"] and state["page_enables"] == 2:
                state["armed"] = False
                return [RuntimeError("cannot receive")]   # one-shot
            return [{"id": cmd["id"], "error": {"code": -32601, "message": "'Page.enable' wasn't found"}}]
        return None
    ws = FakeWS(script=script)
    use(ws)
    bc = zd.core.connection.Connection("ws://fake/devtools/browser/x")
    bc.add_handler(zd.cdp.page.FrameNavigated, lambda e: None)
    await asyncio.wait_for(bc.send(zd.cdp.target.set_discover_targets(True)), 2)
    ws.sent.clear(); state["page_enables"] = 0; state["armed"] = True
    try:
        await asyncio.wait_for(bc.send(zd.cdp.target.create_target("about:blank")), 2)
        print("RESULT: send returned")
    except Exception as e:
        print("RESULT: send raised", type(e).__name__, repr(e))
    print("commands that reached the browser:", [c["method"] for c in ws.sent])
    await bc.aclose()

logging.basicConfig(level=logging.CRITICAL)
asyncio.run(main())
