"""C: a receive error during the automatic Domain.enable fails the caller's
command (already in mapper, not yet sent); send() then still transmits it."""
import asyncio, sys, logging
import zendriver as zd
from fakews import FakeWS, use, tab_for

print(sys.version.split()[0], zd.__file__)

async def main(flat):
    def script(cmd):
        if cmd["method"] == "Network.enable":
            return [RuntimeError("cannot receive")]  # never answered; reader breaks
        return None
    ws = FakeWS(results={"Target.attachToTarget": {"sessionId": "S1"}}, script=script)
    use(ws)
    bc = zd.core.connection.Connection("ws://fake/devtools/browser/x")
    conn = tab_for(bc) if flat else bc
    if flat:
        await asyncio.wait_for(conn.send(zd.cdp.page.bring_to_front()), 2)
    conn.add_handler(zd.cdp.network.RequestWillBeSent, lambda e: None)
    ws.sent.clear()
    try:
        await asyncio.wait_for(conn.send(zd.cdp.input_.insert_text("hello")), 2)
        print("RESULT: send returned")
    except Exception as e:
        print("RESULT: send raised", type(e).__name__, repr(e))
    print("commands that reached the browser:", [c["method"] for c in ws.sent])
    print("enabled_domains:", [m.__name__ for m in conn.enabled_domains])
    if flat:
        await conn.aclose()
    await bc.aclose()

logging.basicConfig(level=logging.CRITICAL)
asyncio.run(main(False))
asyncio.run(main(True))
