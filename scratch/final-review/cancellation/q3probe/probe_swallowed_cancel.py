"""
frozen peer + a browser-level handler whose domain is not enabled yet: the detach send
first sends <Domain>.enable from Connection._register_handlers, whose bare except
swallows the CancelledError of the timeout. does stop() still finish?
run from the worktree root (imports tests.core.test_browser helpers).
"""

import asyncio
import contextlib
import json
import shutil
import subprocess
import sys

from websockets.asyncio.server import serve
from websockets.exceptions import ConnectionClosed

import zendriver as zd
import zendriver.core.browser as zb
from zendriver import cdp
from tests.core.test_browser import _attach_tabs, EXITS_ON_SIGTERM

frozen = False


async def handler(websocket) -> None:  # type: ignore[no-untyped-def]
    with contextlib.suppress(ConnectionClosed):
        async for raw in websocket:
            message = json.loads(raw)
            print("peer got", message["method"], "(frozen)" if frozen else "", flush=True)
            if frozen:
                continue
            result: dict = {}
            if message["method"] == "Target.attachToTarget":
                result = {"sessionId": f"session-{message['params']['targetId']}"}
            reply = {"id": message["id"], "result": result}
            if "sessionId" in message:
                reply["sessionId"] = message["sessionId"]
            await websocket.send(json.dumps(reply))


async def main() -> None:
    global frozen
    print(sys.version.split()[0], zd.__file__)
    zb.STOP_COMMAND_TIMEOUT = 0.5
    browser = zd.Browser(zd.Config(browser_executable_path=sys.executable))
    process = subprocess.Popen([sys.executable, "-c", EXITS_ON_SIGTERM], stdout=subprocess.PIPE)
    assert process.stdout is not None
    process.stdout.readline()
    browser._process, browser._process_pid = process, process.pid

    async with serve(handler, "127.0.0.1", 0) as server:
        port = list(server.sockets)[0].getsockname()[1]
        url = f"ws://127.0.0.1:{port}/devtools/browser/fake"
        await _attach_tabs(browser, url, 1)
        assert browser.connection is not None

        async def on_nav(event: object) -> None:
            pass

        # a handler on the browser connection for a domain that is not enabled yet,
        # e.g. one whose enable failed earlier (Page.enable is not found on the browser target)
        browser.connection.handlers[cdp.page.FrameNavigated] = [on_nav]
        frozen = True

        stop = asyncio.create_task(browser.stop())
        done, _ = await asyncio.wait({stop}, timeout=15)
        print("stop done within 15s:", bool(done))
        if not done:
            stop.print_stack()
            stop.cancel()
            done, _ = await asyncio.wait({stop}, timeout=5)
            print("stop finished after a cancel:", bool(done))
        print("process exited:", process.poll() is not None)
        if process.poll() is None:
            process.kill()
        process.wait()
        process.stdout.close()
        shutil.rmtree(browser.config.user_data_dir, ignore_errors=True)
        if browser.connection and browser.connection.websocket is not None:
            browser.connection.websocket.transport.abort()


asyncio.run(main())
