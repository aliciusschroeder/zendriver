"""
Regression tests for Q4: a start() that fails or is cancelled after the browser
process was launched must not leave that process, its temp profile, or the
registry entry behind (the caller never gets the instance to stop it).

Browser-free: the "browser" is a shell script that sleeps, and the CDP peer is
an in-process websockets server that also answers GET /json/version.
"""

import asyncio
import json
import os
import shutil
import subprocess
from pathlib import Path
from typing import Any

import pytest
import websockets
from websockets.asyncio.server import serve
from websockets.http11 import Request

import zendriver
from zendriver.core import util
from zendriver.core.connection import ProtocolException

print("zendriver imported from", zendriver.__file__)


def _profile_dir(proc: subprocess.Popen[bytes]) -> str:
    for arg in proc.args:  # type: ignore[union-attr]
        if str(arg).startswith("--user-data-dir="):
            return str(arg).split("=", 1)[1]
    raise AssertionError("no --user-data-dir in %r" % (proc.args,))


@pytest.fixture
def fake_chrome(tmp_path: Path) -> Path:
    exe = tmp_path / "fake-chrome"
    exe.write_text("#!/bin/sh\nexec sleep 60\n")
    exe.chmod(0o755)
    return exe


@pytest.fixture
def spawned(monkeypatch: pytest.MonkeyPatch):
    procs: list[subprocess.Popen[bytes]] = []
    orig = util._start_process
    before = set(util.get_registered_instances())

    def spy(*a: Any, **k: Any) -> subprocess.Popen[bytes]:
        p = orig(*a, **k)
        procs.append(p)
        return p

    monkeypatch.setattr(util, "_start_process", spy)
    yield procs
    # safety net: never leave anything behind, whatever the code under test did
    for p in procs:
        if p.poll() is None:
            p.kill()
            p.wait()
        shutil.rmtree(_profile_dir(p), ignore_errors=True)
    for b in set(util.get_registered_instances()) - before:
        util.get_registered_instances().discard(b)
        if not b.config.uses_custom_data_dir:
            shutil.rmtree(b.config.user_data_dir, ignore_errors=True)


class FakeCDP:
    """GET /json/version + a websocket that fails Target.setDiscoverTargets"""

    def __init__(self) -> None:
        self.methods: list[str] = []
        self.port = 0

    def process_request(self, connection: Any, request: Request) -> Any:
        if request.path.startswith("/json/version"):
            return connection.respond(
                200,
                json.dumps(
                    {
                        "Browser": "Fake/1.0",
                        "webSocketDebuggerUrl": "ws://127.0.0.1:%d/devtools/browser/x"
                        % self.port,
                    }
                ),
            )
        return None

    async def handler(self, ws: Any) -> None:
        try:
            async for raw in ws:
                msg = json.loads(raw)
                self.methods.append(msg["method"])
                if msg["method"] == "Target.setDiscoverTargets":
                    await ws.send(
                        json.dumps(
                            {
                                "id": msg["id"],
                                "error": {"code": -32000, "message": "boom"},
                            }
                        )
                    )
                else:
                    await ws.send(json.dumps({"id": msg["id"], "result": {}}))
        except websockets.ConnectionClosed:
            pass


@pytest.fixture
async def fake_cdp():
    peer = FakeCDP()
    async with serve(
        peer.handler, "127.0.0.1", 0, process_request=peer.process_request
    ) as server:
        peer.port = server.sockets[0].getsockname()[1]
        yield peer


async def test_cancelled_start_stops_the_launched_browser(fake_chrome, spawned):
    print("zendriver imported from", zendriver.__file__)
    with pytest.raises(asyncio.TimeoutError):
        # the fake browser never listens, so start() is cancelled in its connect loop
        await asyncio.wait_for(
            zendriver.start(browser_executable_path=fake_chrome, headless=True), 0.3
        )
    assert len(spawned) == 1
    proc = spawned[0]
    assert proc.poll() is not None, "browser process %d still running" % proc.pid
    assert not os.path.exists(_profile_dir(proc)), "temp profile left behind"
    assert not any(
        b._process is proc or b._process_pid == proc.pid
        for b in util.get_registered_instances()
    ), "browser still registered"


async def test_failed_start_stops_the_launched_browser(
    fake_chrome, spawned, fake_cdp, monkeypatch
):
    print("zendriver imported from", zendriver.__file__)
    monkeypatch.setattr(util, "free_port", lambda: fake_cdp.port)
    with pytest.raises(ProtocolException):
        await asyncio.wait_for(zendriver.start(browser_executable_path=fake_chrome), 20)
    assert len(spawned) == 1
    proc = spawned[0]
    assert proc.poll() is not None, "browser process %d still running" % proc.pid
    assert not os.path.exists(_profile_dir(proc)), "temp profile left behind"
    assert not util.get_registered_instances(), "browser still registered"


async def test_failed_attach_does_not_close_the_existing_browser(
    fake_chrome, fake_cdp, spawned
):
    print("zendriver imported from", zendriver.__file__)
    with pytest.raises(ProtocolException):
        # host and port given: attach to a running browser instead of launching one
        await asyncio.wait_for(
            zendriver.start(
                browser_executable_path=fake_chrome,
                host="127.0.0.1",
                port=fake_cdp.port,
            ),
            20,
        )
    assert spawned == []
    assert "Browser.close" not in fake_cdp.methods
    assert not util.get_registered_instances(), "browser still registered"
