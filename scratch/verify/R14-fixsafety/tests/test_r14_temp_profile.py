import asyncio
import logging
import os
import shutil
import socket
import sys
import tempfile
from pathlib import Path

import pytest

import zendriver as zd
from zendriver.core.browser import Browser

print("zendriver under test:", zd.__file__)


@pytest.fixture
def profile_root(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    # temp_profile_dir() uses tempfile.mkdtemp, so every uc_* dir lands here.
    # Chrome keeps its singleton socket in $TMPDIR, which is left untouched.
    root = tmp_path / "profiles"
    root.mkdir()
    monkeypatch.setattr(tempfile, "tempdir", str(root))
    return root


def _profiles(root: Path) -> list[str]:
    return sorted(p.name for p in root.glob("uc_*"))


def _unused_port() -> int:
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    port: int = s.getsockname()[1]
    s.close()
    return port


def test_repr_does_not_create_temp_profile(profile_root: Path) -> None:
    config = zd.Config(headless=True, browser_executable_path=sys.executable)
    text = repr(config)
    str(config)
    assert "user_data_dir" in text
    assert config._user_data_dir is None
    assert not config.uses_custom_data_dir
    assert _profiles(profile_root) == []


def test_repr_still_shows_custom_user_data_dir(tmp_path: Path) -> None:
    config = zd.Config(
        user_data_dir=tmp_path / "mine", browser_executable_path=sys.executable
    )
    assert f"user_data_dir = {tmp_path / 'mine'}" in repr(config)


async def test_browsers_from_printed_template_get_distinct_profiles(
    profile_root: Path,
) -> None:
    config = zd.Config(headless=True, browser_executable_path=sys.executable)
    print(config)
    logging.getLogger("r14").info("config: %s", config)
    b1 = Browser(config)
    b2 = Browser(config)
    try:
        assert b1.config.user_data_dir != b2.config.user_data_dir
    finally:
        for b in (b1, b2):
            shutil.rmtree(b.config.user_data_dir, ignore_errors=True)


@pytest.mark.parametrize("debug", [False, True])
async def test_failed_start_bad_executable_leaks_no_profile(
    profile_root: Path, caplog: pytest.LogCaptureFixture, debug: bool
) -> None:
    if debug:
        caplog.set_level(logging.DEBUG, logger="zendriver")
    for _ in range(3):
        with pytest.raises(FileNotFoundError):
            await asyncio.wait_for(
                zd.start(browser_executable_path="/nonexistent/chrome", headless=True),
                30,
            )
    assert _profiles(profile_root) == []


async def test_failed_connect_to_existing_browser_leaks_no_profile(
    profile_root: Path,
) -> None:
    with pytest.raises(Exception, match="Failed to connect to browser"):
        await asyncio.wait_for(
            zd.start(
                host="127.0.0.1",
                port=_unused_port(),
                browser_executable_path=sys.executable,
                browser_connection_max_tries=0,
            ),
            30,
        )
    assert _profiles(profile_root) == []


async def test_stop_of_never_started_browser_leaves_no_profile(
    profile_root: Path,
) -> None:
    config = zd.Config(headless=True, browser_executable_path=sys.executable)
    b = Browser(config)
    await b.stop()
    await b.stop()
    assert _profiles(profile_root) == []


@pytest.mark.skipif(
    shutil.which("chromium") is None, reason="needs a chromium binary on PATH"
)
async def test_printed_template_two_real_browsers_keep_their_profiles(
    profile_root: Path,
) -> None:
    config = zd.Config(headless=True, browser_connection_max_tries=40)
    repr(config)
    started: list[zd.Browser] = []
    try:
        b1 = await asyncio.wait_for(zd.start(config), 60)
        started.append(b1)
        b2 = await asyncio.wait_for(zd.start(config), 60)
        started.append(b2)
        assert b1.config.user_data_dir != b2.config.user_data_dir
        await b2.stop()
        assert os.path.isdir(b1.config.user_data_dir)
    finally:
        for b in started:
            await b.stop()
    assert _profiles(profile_root) == []
