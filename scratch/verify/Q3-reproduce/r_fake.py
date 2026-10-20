"""Browser-free reproducers for Browser._stop using a fake CDP peer.

scenarios:
  close_silent   : no targets; peer never answers Browser.close -> stop() hangs, process never terminated
  detach_silent  : one flat session target; peer never answers Target.detachFromTarget -> stop() hangs
  detach_abort   : one flat session target; peer drops the TCP connection (no close frame) on
                   Target.detachFromTarget -> stop() raises ConnectionClosedError, process+profile leak
  concurrent     : no targets; peer answers Browser.close; fake process exits 0.4s after SIGTERM;
                   second stop() starts 0.1s later -> AttributeError
"""
import asyncio
import json
import os
import shutil
import subprocess
import sys
import traceback

import websockets
from websockets.asyncio.server import serve

import zendriver as zd
from zendriver.core.browser import Browser
from zendriver.core.connection import Connection

print("zendriver from", zd.__file__, "python", sys.version.split()[0], "websockets", websockets.__version__)

SCEN = sys.argv[1]
received = []


async def handler(ws):
    try:
        async for raw in ws:
            msg = json.loads(raw)
            received.append(msg["method"])
            m = msg["method"]
            if SCEN == "close_silent" and m == "Browser.close":
                continue
            if SCEN == "detach_silent" and m == "Target.detachFromTarget":
                continue
            if SCEN == "detach_abort" and m == "Target.detachFromTarget":
                ws.transport.abort()  # drop TCP without a close frame (like a crashed Chrome)
                return
            reply = {"id": msg["id"], "result": {}}
            if "sessionId" in msg:
                reply["sessionId"] = msg["sessionId"]
            await ws.send(json.dumps(reply))
    except websockets.exceptions.ConnectionClosed:
        pass


def stack_of(t):
    out = []
    c = t.get_coro()
    while c is not None and hasattr(c, "cr_frame"):
        f = c.cr_frame
        if f is not None:
            out.append(f"{f.f_code.co_qualname}:{f.f_lineno}")
        c = getattr(c, "cr_await", None)
    return " -> ".join(out) + f" | awaiting {type(c).__name__}"


async def make_browser(url, proc_cmd):
    cfg = zd.Config(headless=False)
    b = Browser(cfg)
    udd = b.config.user_data_dir  # creates the temp profile dir like start() would
    os.makedirs(udd, exist_ok=True)
    b._process = subprocess.Popen(proc_cmd)
    b._process_pid = b._process.pid
    b.connection = Connection(url, _owner=b)
    await b.connection.aopen()
    return b, udd


async def main():
    async with serve(handler, "127.0.0.1", 0) as server:
        port = server.sockets[0].getsockname()[1]
        url = f"ws://127.0.0.1:{port}/devtools/browser/fake"
        if SCEN == "concurrent":
            cmd = ["sh", "-c", 'trap "sleep 0.4; exit 0" TERM; while :; do sleep 0.05; done']
        else:
            cmd = ["sleep", "1000"]
        b, udd = await make_browser(url, cmd)
        proc = b._process
        try:
            if SCEN in ("detach_silent", "detach_abort"):
                # a flat-session target carried by the browser connection
                sess = Connection(url, _owner=b)
                sess._session_parent = b.connection
                sess.session_id = "SESSION-1"
                sess.websocket = b.connection.websocket
                b.connection._sessions["SESSION-1"] = sess
                b.targets.append(sess)
            if SCEN == "concurrent":
                await asyncio.sleep(0.2)  # let sh install its trap

                async def second():
                    await asyncio.sleep(0.1)
                    return await b.stop()

                res = await asyncio.wait_for(
                    asyncio.gather(b.stop(), second(), return_exceptions=True), 20)
                print("results:", [f"{type(r).__name__}: {r}" if isinstance(r, BaseException) else r for r in res])
                print("proc returncode:", proc.poll(), "| profile exists:", os.path.exists(udd))
                return
            t = asyncio.create_task(b.stop())
            done, _ = await asyncio.wait({t}, timeout=8)
            if t in done:
                e = t.exception()
                if e is not None:
                    tb = traceback.extract_tb(e.__traceback__)
                    print("stop() RAISED", type(e).__name__, e, "| tb:",
                          " -> ".join(f"{fr.name}:{fr.lineno}" for fr in tb))
                else:
                    print("stop() returned normally")
            else:
                print("stop() STILL PENDING after 8s:", stack_of(t))
                t.cancel()
                await asyncio.gather(t, return_exceptions=True)
            print("methods received by peer:", received)
            print("proc returncode (None = still running):", proc.poll(),
                  "| b._process still set:", b._process is not None,
                  "| profile exists:", os.path.exists(udd))
        finally:
            if proc.poll() is None:
                proc.kill()
                proc.wait()
            if b.connection is not None and b.connection.websocket is not None:
                try:
                    await asyncio.wait_for(b.connection.aclose(), 5)
                except Exception:
                    pass
            shutil.rmtree(udd, ignore_errors=True)


asyncio.run(asyncio.wait_for(main(), 60))
