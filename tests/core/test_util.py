import asyncio
import subprocess
import sys
from pathlib import Path

import pytest
from pytest_mock import MockerFixture

import zendriver as zd
from zendriver.core import util
from zendriver.core.config import is_posix

# a python process stands in for the browser in these tests


def _start_python(code: str) -> subprocess.Popen[bytes]:
    return util._start_process(sys.executable, ["-c", code], is_posix)


def _kill(process: subprocess.Popen[bytes]) -> None:
    if process.poll() is None:
        process.kill()
    process.wait(10)


async def _wait_for_file(path: Path) -> None:
    async def wait() -> None:
        while not path.exists():
            await asyncio.sleep(0.05)

    await asyncio.wait_for(wait(), 10)


async def test_start_process_does_not_block_a_process_that_writes_a_lot() -> None:
    # far more than a pipe holds: a process writing to a pipe nobody reads never exits
    process = _start_python(
        "import sys\n"
        "for _ in range(1024):\n"
        "    sys.stdout.buffer.write(b'o' * 1023 + b'\\n')\n"
        "    sys.stderr.buffer.write(b'e' * 1023 + b'\\n')\n"
        "sys.stderr.buffer.write(b'last line\\n')\n"
    )
    try:
        try:
            await asyncio.to_thread(process.wait, 10)
        except subprocess.TimeoutExpired:
            pytest.fail("the process blocked writing to a pipe nobody reads")
        stderr = await asyncio.wait_for(util._read_process_stderr(process), 10)
    finally:
        _kill(process)

    assert process.returncode == 0
    assert stderr.endswith("last line\n")
    assert len(stderr) <= 2**16


async def test_read_process_stderr_returns_output_of_a_running_process(
    tmp_path: Path,
) -> None:
    written = tmp_path / "written"
    process = _start_python(
        "import pathlib, sys, time\n"
        "sys.stderr.buffer.write(b'Cannot start http server for devtools.\\n')\n"
        "sys.stderr.buffer.flush()\n"
        f"pathlib.Path({str(written)!r}).touch()\n"
        "time.sleep(60)\n"
    )
    try:
        await _wait_for_file(written)
        stderr = await asyncio.wait_for(util._read_process_stderr(process), 10)
        assert process.poll() is None
    finally:
        _kill(process)

    assert stderr == "Cannot start http server for devtools.\n"


async def test_read_process_stderr_returns_output_of_an_exited_process() -> None:
    process = _start_python(
        "import sys\nsys.stderr.buffer.write(b'unknown flag\\n')\nsys.exit(1)\n"
    )
    try:
        await asyncio.to_thread(process.wait, 10)
        stderr = await asyncio.wait_for(util._read_process_stderr(process), 10)
    finally:
        _kill(process)

    assert stderr == "unknown flag\n"


async def test_read_process_stderr_replaces_bytes_that_are_not_utf8() -> None:
    process = _start_python("import sys\nsys.stderr.buffer.write(b'bad \\xff\\n')\n")
    try:
        await asyncio.to_thread(process.wait, 10)
        stderr = await asyncio.wait_for(util._read_process_stderr(process), 10)
    finally:
        _kill(process)

    assert stderr == "bad \ufffd\n"


async def test_start_failure_logs_stderr_of_a_browser_that_is_still_running(
    tmp_path: Path, mocker: MockerFixture, caplog: pytest.LogCaptureFixture
) -> None:
    written = tmp_path / "written"
    config = zd.Config(
        browser_executable_path=sys.executable,
        user_data_dir=tmp_path / "profile",
        browser_connection_max_tries=1,
        browser_connection_timeout=0.1,
    )
    # python runs this and leaves the browser arguments after it alone
    config._default_browser_args = [
        "-c",
        "import pathlib, sys, time\n"
        "sys.stderr.buffer.write(b'Cannot start http server for devtools.\\n')\n"
        "sys.stderr.buffer.flush()\n"
        f"pathlib.Path({str(written)!r}).touch()\n"
        "time.sleep(60)\n",
    ]

    async def test_connection(self: zd.Browser) -> bool:
        # the debugging port never opens, but let the browser report why first
        await _wait_for_file(written)
        return False

    mocker.patch.object(zd.Browser, "test_connection", test_connection)
    with caplog.at_level("INFO"):
        with pytest.raises(Exception, match="Failed to connect to browser"):
            await asyncio.wait_for(zd.start(config), 30)

    # the arguments logged at start contain the message too, so look at the stderr line
    [stderr] = [m for m in caplog.messages if m.startswith("Browser stderr: ")]
    assert stderr == "Browser stderr: Cannot start http server for devtools.\n"
