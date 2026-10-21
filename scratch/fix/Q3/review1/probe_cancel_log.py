"""
browser-free probe: cancel stop() while it waits for Target.detachFromTarget and
check whether asyncio logs 'exception was never retrieved', whether the
cancellation propagates, and whether the atexit fallback is kept.
"""

import asyncio
import contextlib
import gc
import json
import subprocess
import sys

import asyncio_atexit
from websockets.asyncio.server import serve
from websockets.exceptions import ConnectionClosed

import zendriver as zd
from zendriver import cdp

logged: list[str] = []


async def main() -> None:
    loop = asyncio.get_running_loop()
    loop.set_exception_handler(lambda l, ctx: logged.append(ctx.get("message", "")))

    async def handler(ws):  # type: ignore[no-untyped-def]
        with contextlib.suppress(ConnectionClosed):
            async for raw in ws:
                m = json.loads(raw)
                if m["method"] == "Target.detachFromTarget":
                    continue  # never answers
                result = {}
                if m["method"] == "Target.attachToTarget":
                    result = {"sessionId": "s-" + m["params"]["targetId"]}
                r = {"id": m["id"], "result": result}
                if "sessionId" in m:
                    r["sessionId"] = m["sessionId"]
                await ws.send(json.dumps(r))

    async with serve(handler, "127.0.0.1", 0) as server:
        port = list(server.sockets)[0].getsockname()[1]
        url = f"ws://127.0.0.1:{port}/devtools/browser/x"
        b = zd.Browser(zd.Config(browser_executable_path=sys.executable))
        p = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(60)"])
        b._process, b._process_pid = p, p.pid
        asyncio_atexit.register(b._atexit_cleanup)
        b.connection = zd.Connection(url, _owner=b)
        for i in range(2):
            ti = cdp.target.TargetInfo(
                target_id=cdp.target.TargetID(f"t{i}"),
                type_="page",
                title="",
                url="about:blank",
                attached=False,
                can_access_opener=False,
            )
            t = zd.Tab(url, target=ti, browser=b)
            b.targets.append(t)
            await t.aopen()

        task = asyncio.create_task(b.stop())
        await asyncio.sleep(0.3)
        task.cancel()
        res = await asyncio.gather(task, return_exceptions=True)
        print("stop() result after cancel:", repr(res[0]))
        entry = asyncio_atexit._get_entry()
        print("atexit kept:", b._atexit_cleanup in entry.callbacks)
        del res, task
        for _ in range(3):
            gc.collect()
            await asyncio.sleep(0.05)
        print("loop exception handler messages:", logged)
        # let the atexit fallback finish the job
    print("leaving main")


asyncio.run(main())
print("process returncode after asyncio.run:", "see atexit")
