"""controls: same fake peer, but with a gap between the two frames; plus the stuck stack for B14.7"""

import asyncio
import json
import sys
from types import SimpleNamespace

sys.path.insert(0, sys.argv[1])  # tests dir
import test_r22_session_attach as t  # noqa: E402
from websockets.asyncio.server import serve  # noqa: E402

import zendriver  # noqa: E402
from zendriver import cdp  # noqa: E402
from zendriver.core.connection import Connection  # noqa: E402

print("zendriver:", zendriver.__file__, "python:", sys.version.split()[0])


class GapChrome(t.FakeChrome):
    gap = 0.05

    def burst(self, ws, *messages):  # type: ignore[override]
        first, *rest = messages
        t.FakeChrome.burst(ws, first)
        if rest:

            async def later() -> None:
                await asyncio.sleep(self.gap)
                t.FakeChrome.burst(ws, *rest)

            asyncio.create_task(later())


async def setup(fake):
    server = await serve(fake.handler, "127.0.0.1", 0).__aenter__()
    port = server.sockets[0].getsockname()[1]
    bc = Connection(f"ws://127.0.0.1:{port}/devtools/browser/b")
    owner = SimpleNamespace(connection=bc, config=None)
    target = cdp.target.TargetInfo(
        target_id=cdp.target.TargetID("T1"), type_="page", title="", url="",
        attached=False, can_access_opener=False,
    )
    tab = Connection("ws://unused", target=target, _owner=owner)
    return server, bc, tab


async def run(label, fake, mode):
    server, bc, tab = await setup(fake)
    try:
        if mode == "evaluate":
            await tab.aopen()
            fake.detach_with_evaluate_reply = True
        else:
            fake.detach_with_attach_reply = True
        task = asyncio.ensure_future(tab.send(cdp.runtime.evaluate("1+1")))
        done, _ = await asyncio.wait({task}, timeout=2)
        if not done:
            print(f"[{label}] HANG after 2s: session_id={tab.session_id} sessions={list(bc._sessions)} "
                  f"tab.mapper={list(tab.mapper)} browser.mapper={list(bc.mapper)}")
            task.print_stack(file=sys.stdout)
            task.cancel()
        else:
            exc = task.exception()
            print(f"[{label}] result:", repr(exc).splitlines()[0] if exc else task.result())
    finally:
        await tab.aclose()
        await bc.aclose()
        server.close()


async def main():
    await run("A1.5 burst", t.FakeChrome(), "evaluate")
    await run("A1.5 50ms gap", GapChrome(), "evaluate")
    await run("B14.7 burst", t.FakeChrome(), "attach")
    await run("B14.7 50ms gap", GapChrome(), "attach")


asyncio.run(asyncio.wait_for(main(), 60))
