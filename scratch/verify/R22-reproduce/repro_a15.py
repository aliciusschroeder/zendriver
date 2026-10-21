"""A1.5: a session reply in the same burst as Target.detachedFromTarget is discarded."""

import asyncio
import sys

import zendriver
from zendriver import cdp
from zendriver.core.connection import Connection, ProtocolException

from fakepeer import FakePeer, make_tab

print("python", sys.version.split()[0], "zendriver from", zendriver.__file__)


async def trial(delay, n=20):
    peer = await FakePeer().start()
    peer.detach_after_method = "Runtime.evaluate"
    peer.detach_after_method_delay = delay
    bc = Connection(peer.url)
    ok = err = other = 0
    example = None
    try:
        for i in range(n):
            tab = make_tab(bc, Connection, cdp)
            try:
                res = await asyncio.wait_for(
                    tab.send(cdp.runtime.evaluate("1+1")), 5
                )
                ok += 1
            except ProtocolException as e:
                err += 1
                example = str(e).splitlines()[0]
            except Exception as e:  # timeouts etc
                other += 1
                example = repr(e)
            # make sure the detach has been processed before the next trial
            await asyncio.sleep(max(delay, 0) + 0.05)
        replied = sum(
            1
            for f in peer.sent_frames
            if f.get("sessionId") and "result" in f and f.get("result", {}).get("result")
        )
        print(
            f"delay={delay}: peer sent successful evaluate replies: {replied}; "
            f"caller success={ok} ProtocolException={err} other={other} example={example!r}"
        )
    finally:
        await bc.aclose()
        await peer.stop()


async def main():
    await trial(0.0)
    await trial(0.05)


asyncio.run(main())
