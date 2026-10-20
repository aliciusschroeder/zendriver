import asyncio, json
import websockets
import zendriver as zd
from zendriver.core.connection import ProtocolException

async def main():
    b = zd.Browser(zd.Config(headless=True))  # not started; __aexit__ does not touch the process
    for exc in [
        websockets.exceptions.ConnectionClosedError(None, None),
        json.JSONDecodeError("Expecting value", "doc", 0),
        ProtocolException({"code": -32000, "message": "No node with given id found"}),
    ]:
        try:
            async with b:
                raise exc
        except BaseException as e:
            print(f"raised {type(exc).__name__:22} -> caught {type(e).__name__}: {e!s:.80} | code={getattr(e,'code','-')}")

asyncio.run(main())
