"""B14.7: detachedFromTarget in the same burst as the attach reply is dropped; later sends hang."""

import asyncio
import sys

import zendriver
from zendriver import cdp
from zendriver.core.connection import Connection, ProtocolException

from fakepeer import FakePeer, make_tab

print("python", sys.version.split()[0], "zendriver from", zendriver.__file__)


async def one_send(tab, label, peer, bc):
    t = asyncio.ensure_future(tab.send(cdp.runtime.evaluate("1")))
    done, _ = await asyncio.wait({t}, timeout=3)
    if not done:
        print(f"  {label}: HANG (not done after 3s)")
        print(
            f"    tab.session_id={tab.session_id} bc._sessions={list(bc._sessions)} "
            f"bc.mapper={list(bc.mapper)} tab.mapper={list(tab.mapper)} "
            f"peer alive sessions={sorted(peer.alive_sessions)}"
        )
        print("    last peer frames:", peer.sent_frames[-3:])
        print("    stack of the stuck send task:")
        t.print_stack(file=sys.stdout)
        t.cancel()
        try:
            await t
        except BaseException:
            pass
        return "hang"
    try:
        t.result()
        print(f"  {label}: success")
        return "ok"
    except ProtocolException as e:
        print(f"  {label}: ProtocolException {str(e).splitlines()[0]!r}")
        return "pe"
    except Exception as e:
        print(f"  {label}: {e!r}")
        return "other"


async def trial(delay):
    print(f"--- detach after attach reply, delay={delay}")
    peer = await FakePeer().start()
    peer.detach_after_attach = delay
    bc = Connection(peer.url)
    try:
        tab = make_tab(bc, Connection, cdp)
        await one_send(tab, "first send", peer, bc)
        await asyncio.sleep(max(delay, 0) + 0.1)
        await one_send(tab, "second send", peer, bc)
    finally:
        await bc.aclose()
        await peer.stop()


async def main():
    await trial(0.0)
    await trial(0.2)


asyncio.run(main())
