import asyncio
import websockets
import zendriver as zd
from zendriver import cdp
from zendriver.core.connection import Connection, ProtocolException

async def main():
    browser = await zd.start(headless=True)
    try:
        tab = await browser.get("about:blank")
        # 1. ProtocolException from a real command inside `async with tab:`
        try:
            async with tab:
                await tab.send(cdp.dom.get_document())  # fine
                await tab.send(cdp.dom.resolve_node(node_id=cdp.dom.NodeId(999999)))
        except ProtocolException as e:
            print("1. caught ProtocolException code=%r message=%r" % (e.code, e.message[:60]))
        # 2. multi-arg exceptions are replaced by TypeError
        for exc in (UnicodeDecodeError("utf-8", b"\xff", 0, 1, "bad"),
                    websockets.exceptions.ConnectionClosedError(None, None),
                    ExceptionGroup("eg", [ValueError("x")])):
            try:
                async with tab:
                    raise exc
            except BaseException as e:
                print("2. raised %s -> caught %s: %s" % (type(exc).__name__, type(e).__name__, e))
        # 3. KeyError args get wrapped
        try:
            async with tab:
                {}["k"]
        except KeyError as e:
            print("3. KeyError args:", e.args)
    finally:
        await browser.stop()
    # baseline for comparison
    try:
        await browser.connection.send(cdp.dom.resolve_node(node_id=cdp.dom.NodeId(999999))) if False else None
    except Exception:
        pass

asyncio.run(asyncio.wait_for(main(), 50))
