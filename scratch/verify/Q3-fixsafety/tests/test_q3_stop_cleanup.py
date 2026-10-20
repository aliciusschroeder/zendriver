"""
Q3 regression tests: Browser.stop()/_stop()/_atexit_cleanup must always get to
terminate the process and remove the temporary profile. Browser-free: a fake CDP
peer stands in for chrome and a plain python child process for its process.
"""

import asyncio
import json
import os
import shutil
import subprocess
import sys
from typing import Any, Callable

import asyncio_atexit
import pytest
from websockets.asyncio.server import ServerConnection, serve

import zendriver
from zendriver import cdp
from zendriver.core import browser as browser_module
from zendriver.core.browser import Browser
from zendriver.core.config import Config
from zendriver.core.connection import Connection
from zendriver.core.tab import Tab

print("zendriver under test:", zendriver.__file__)

SLEEPER = [sys.executable, "-c", "import time; time.sleep(120)"]
# ignores SIGTERM, so that stop() has to fall through to kill()
STUBBORN = [
    sys.executable,
    "-c",
    "import signal, time; signal.signal(signal.SIGTERM, signal.SIG_IGN); "
    "print('ready', flush=True); time.sleep(120)",
]


def make_browser() -> Browser:
    config = Config(browser_executable_path=sys.executable, headless=False)
    b = Browser(config)
    # creates the temporary profile dir, as start() does through config()
    assert os.path.isdir(b.config.user_data_dir)
    return b


def spawn(argv: list[str]) -> subprocess.Popen[bytes]:
    p = subprocess.Popen(argv, stdout=subprocess.PIPE)
    if argv is STUBBORN:
        assert p.stdout is not None
        assert p.stdout.readline().strip() == b"ready"
    return p


def reap(b: Browser, p: subprocess.Popen[bytes]) -> None:
    if p.poll() is None:
        p.kill()
    p.wait()
    shutil.rmtree(b.config.user_data_dir, ignore_errors=True)


class FakeChrome:
    """answers every command, except those listed in `on`"""

    def __init__(self, on: dict[str, Callable[[ServerConnection, dict[str, Any]], Any]]):
        self.on = on
        self.seen: list[str] = []

    async def handler(self, ws: ServerConnection) -> None:
        async for raw in ws:
            msg = json.loads(raw)
            method = msg["method"]
            self.seen.append(method)
            if method in self.on:
                await self.on[method](ws, msg)
                continue
            result: dict[str, Any] = {}
            if method == "Target.attachToTarget":
                result = {"sessionId": "S-" + msg["params"]["targetId"]}
            reply: dict[str, Any] = {"id": msg["id"], "result": result}
            if "sessionId" in msg:
                reply["sessionId"] = msg["sessionId"]
            await ws.send(json.dumps(reply))


async def never_answer(ws: ServerConnection, msg: dict[str, Any]) -> None:
    return None


async def drop_connection(ws: ServerConnection, msg: dict[str, Any]) -> None:
    # like a crashed chrome: no close frame
    ws.transport.abort()


async def attach_browser(b: Browser, url: str, n_tabs: int) -> list[Tab]:
    b.connection = Connection(url, _owner=b)
    await b.connection.aopen()
    tabs = []
    for i in range(n_tabs):
        info = cdp.target.TargetInfo(
            target_id=cdp.target.TargetID(f"T{i}"),
            type_="page",
            title="",
            url="about:blank",
            attached=False,
            can_access_opener=False,
        )
        t = Tab(url, target=info, browser=b)
        b.targets.append(t)
        await t.aopen()
        assert t.session_id == f"S-T{i}"
        tabs.append(t)
    return tabs


@pytest.mark.parametrize("hang_on", ["Target.detachFromTarget", "Browser.close"])
async def test_stop_terminates_an_unresponsive_browser(
    hang_on: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    # members B13.5, A3.4, B15.3, B16.2
    monkeypatch.setattr(browser_module, "STOP_COMMAND_TIMEOUT", 0.5, raising=False)
    fake = FakeChrome({hang_on: never_answer})
    async with serve(fake.handler, "127.0.0.1", 0) as server:
        port = server.sockets[0].getsockname()[1]
        b = make_browser()
        p = spawn(SLEEPER)
        b._process, b._process_pid = p, p.pid
        try:
            await attach_browser(b, f"ws://127.0.0.1:{port}", n_tabs=3)
            task = asyncio.ensure_future(b.stop())
            done, _ = await asyncio.wait({task}, timeout=10)
            if not done:
                task.print_stack(file=sys.stdout)
                task.cancel()
                await asyncio.gather(task, return_exceptions=True)
            assert done, "stop() still waiting on %s after 10s" % hang_on
            task.result()
            assert p.poll() is not None, "browser process was not terminated"
            assert not os.path.exists(b.config.user_data_dir)
        finally:
            reap(b, p)


async def test_stop_cleans_up_when_the_connection_drops_during_detach() -> None:
    # member A1.2
    fake = FakeChrome({"Target.detachFromTarget": drop_connection})
    async with serve(fake.handler, "127.0.0.1", 0) as server:
        port = server.sockets[0].getsockname()[1]
        b = make_browser()
        p = spawn(SLEEPER)
        b._process, b._process_pid = p, p.pid
        try:
            await attach_browser(b, f"ws://127.0.0.1:{port}", n_tabs=2)
            await asyncio.wait_for(b.stop(), 20)
            assert p.poll() is not None
            assert b._process is None
            assert not os.path.exists(b.config.user_data_dir)
        finally:
            reap(b, p)


async def test_concurrent_stop_calls_do_not_raise() -> None:
    # member A3.11: the second stop() reaps the process while the first sleeps
    b = make_browser()
    p = spawn(SLEEPER)
    b._process, b._process_pid = p, p.pid
    try:
        first = asyncio.ensure_future(b.stop())
        await asyncio.sleep(0.1)
        second = asyncio.ensure_future(b.stop())
        results = await asyncio.wait_for(
            asyncio.gather(first, second, return_exceptions=True), 20
        )
        assert results == [None, None]
        assert p.poll() is not None
        assert not os.path.exists(b.config.user_data_dir)
    finally:
        reap(b, p)


@pytest.mark.parametrize("argv", [SLEEPER, STUBBORN], ids=["terminated", "killed"])
def test_atexit_cleanup_under_asyncio_run(
    argv: list[str], capfd: pytest.CaptureFixture[str]
) -> None:
    # members A3.1, B16.3: asyncio.run shuts the default executor down before
    # the asyncio_atexit callbacks run inside loop.close()
    state: dict[str, Any] = {}

    async def main() -> None:
        b = make_browser()
        p = spawn(argv)
        b._process, b._process_pid = p, p.pid
        asyncio_atexit.register(b._atexit_cleanup)  # as Browser.create does
        state["b"], state["p"] = b, p
        # returns without calling stop()

    try:
        asyncio.run(main())
        err = capfd.readouterr().err
        assert "Unhandled exception in asyncio atexit callback" not in err, err
        assert state["p"].poll() is not None
        assert not os.path.exists(state["b"].config.user_data_dir)
    finally:
        if "b" in state:
            reap(state["b"], state["p"])


async def test_cancelled_stop_keeps_the_atexit_cleanup() -> None:
    # aggravating detail of B13.5/A3.4/B16.2: wait_for(stop(), t) dropped the atexit hook
    b = make_browser()
    p = spawn(STUBBORN)
    b._process, b._process_pid = p, p.pid
    asyncio_atexit.register(b._atexit_cleanup)
    try:
        with pytest.raises(asyncio.TimeoutError):
            await asyncio.wait_for(b.stop(), 0.5)
        entry = asyncio_atexit._get_entry()
        assert b._atexit_cleanup in entry.callbacks
    finally:
        asyncio_atexit.unregister(b._atexit_cleanup)
        reap(b, p)
