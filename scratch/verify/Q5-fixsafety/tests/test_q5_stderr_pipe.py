"""Regression tests for Q5: the browser's stdout/stderr pipes must not fill up.

Browser-free: a small Python script stands in for the browser executable.
"""

import asyncio
import logging
import os
import stat
import subprocess
import sys
from pathlib import Path

import pytest

import zendriver
from zendriver.core import util


def test_which_zendriver() -> None:
    print("zendriver imported from", zendriver.__file__)


def _fake_browser(tmp_path: Path, body: str) -> Path:
    script = tmp_path / "fake-browser"
    script.write_text(f"#!{sys.executable}\nimport sys, time\n{body}\n")
    script.chmod(script.stat().st_mode | stat.S_IXUSR)
    return script


def _kill(process: subprocess.Popen[bytes]) -> None:
    if process.poll() is None:
        process.kill()
    process.wait(10)


async def test_browser_does_not_block_when_it_logs_more_than_a_pipe_holds(
    tmp_path: Path,
) -> None:
    # writes 1 MiB to stderr and 1 MiB to stdout, then exits.
    # a browser blocked on a full pipe never gets to exit
    exe = _fake_browser(
        tmp_path,
        "for _ in range(1024):\n"
        "    sys.stderr.buffer.write(b'e' * 1023 + b'\\n'); sys.stderr.flush()\n"
        "for _ in range(1024):\n"
        "    sys.stdout.buffer.write(b'o' * 1023 + b'\\n'); sys.stdout.flush()\n"
        "sys.stderr.buffer.write(b'LAST LINE\\n'); sys.stderr.flush()\n",
    )
    process = util._start_process(exe, [], is_posix=os.name == "posix")
    try:
        try:
            returncode = await asyncio.to_thread(process.wait, 15)
        except subprocess.TimeoutExpired:
            pytest.fail("the browser process blocked writing to an undrained pipe")
        assert returncode == 0
        stderr = await util._read_process_stderr(process)
        assert stderr.endswith("LAST LINE\n")
        assert len(stderr) <= 2**16
    finally:
        _kill(process)


async def test_stderr_of_a_running_browser_is_read(tmp_path: Path) -> None:
    exe = _fake_browser(
        tmp_path,
        "sys.stderr.write('[ERROR:devtools_http_handler.cc(310)] Cannot start http server for devtools.\\n')\n"
        "sys.stderr.flush()\n"
        "time.sleep(60)\n",
    )
    process = util._start_process(exe, [], is_posix=os.name == "posix")
    try:
        await asyncio.sleep(1.0)  # let it write
        assert process.poll() is None
        stderr = await asyncio.wait_for(util._read_process_stderr(process), 10)
        assert "Cannot start http server for devtools." in stderr
    finally:
        _kill(process)


async def test_stderr_of_an_exited_browser_is_read(tmp_path: Path) -> None:
    exe = _fake_browser(tmp_path, "sys.stderr.write('boom: bad flag\\n'); sys.exit(1)\n")
    process = util._start_process(exe, [], is_posix=os.name == "posix")
    try:
        await asyncio.to_thread(process.wait, 15)
        stderr = await asyncio.wait_for(util._read_process_stderr(process), 10)
        assert stderr == "boom: bad flag\n"
    finally:
        _kill(process)


async def test_start_failure_logs_stderr_of_running_browser(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    exe = _fake_browser(
        tmp_path,
        "sys.stderr.write('Cannot start http server for devtools.\\n'); sys.stderr.flush()\n"
        "time.sleep(60)\n",
    )

    async def never_connects(self: zendriver.Browser) -> bool:
        return False

    monkeypatch.setattr(zendriver.Browser, "test_connection", never_connects)
    config = zendriver.Config(
        headless=True,
        browser_executable_path=str(exe),
        user_data_dir=str(tmp_path / "profile"),
        browser_connection_max_tries=2,
        browser_connection_timeout=0.5,
    )
    with caplog.at_level(logging.INFO, logger="zendriver"):
        with pytest.raises(Exception, match="Failed to connect to browser"):
            await asyncio.wait_for(zendriver.start(config), 30)
    assert "Cannot start http server for devtools." in caplog.text
