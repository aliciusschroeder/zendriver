"""Probe A: a result the cdp parser cannot parse kills the listener and hangs send()."""
import asyncio

from fakecdp import FakeCDP

import zendriver as zd
from zendriver.core.connection import Connection


def behaviour(msg):
    if msg["method"] == "Target.getTargetInfo":
        return {}  # missing "targetInfo"
    if msg["method"] == "Storage.getCookies":
        # cookie with a sameSite value newer than the generated enum
        return {
            "cookies": [
                {
                    "name": "a", "value": "b", "domain": "x", "path": "/",
                    "expires": -1, "size": 2, "httpOnly": False, "secure": False,
                    "session": True, "priority": "Medium", "sameParty": False,
                    "sourceScheme": "Secure", "sourcePort": 443,
                    "sameSite": "SomeFutureValue",
                }
            ]
        }
    return {}


async def main() -> None:
    fake = FakeCDP(behaviour)
    url = await fake.start()
    conn = Connection(url)
    for cmd in (zd.cdp.target.get_target_info(), zd.cdp.storage.get_cookies()):
        try:
            r = await asyncio.wait_for(conn.send(cmd), 3)
            print("result", r)
        except asyncio.TimeoutError:
            print("send() HUNG (timed out after 3s)")
        except Exception as e:
            print("send() raised", type(e).__name__, e)
        lt = conn.listener.task
        print("listener done:", lt.done(), "exception:", repr(lt.exception()) if lt.done() and not lt.cancelled() else None)
        print("mapper after:", conn.mapper)
    # the connection recovers for later sends because send() restarts the listener
    r = await asyncio.wait_for(conn.send(zd.cdp.target.set_discover_targets(discover=True)), 3)
    print("later send ok:", r)
    await conn.aclose()
    await fake.stop()


asyncio.run(main())
