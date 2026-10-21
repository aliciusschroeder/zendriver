"""Regression tests for R15 (config argument assembly). Browser-free."""

import collections
import pathlib
import sys

import pytest

import zendriver as zd
from zendriver.core import util

print("zendriver imported from", zd.__file__)


def test_print_import_path() -> None:
    print("zendriver imported from", zd.__file__)


def make_config(tmp_path: pathlib.Path, **kwargs: object) -> zd.Config:
    # an existing executable and an explicit profile dir, so nothing is
    # autodetected and no temp profile is created
    return zd.Config(
        browser_executable_path=sys.executable,
        user_data_dir=tmp_path / "profile",
        **kwargs,  # type: ignore[arg-type]
    )


def duplicates(args: list[str]) -> dict[str, int]:
    return {a: n for a, n in collections.Counter(args).items() if n > 1}


# SEED-K1
def test_browser_args_property_merges_disable_features_and_dedupes(
    tmp_path: pathlib.Path,
) -> None:
    config = make_config(
        tmp_path,
        browser_args=["--disable-features=Foo", "--mute-audio", "--mute-audio"],
    )
    args = config.browser_args
    disable = [a for a in args if a.startswith("--disable-features=")]
    assert len(disable) == 1 and "Foo" in disable[0].split("=", 1)[1].split(",")
    assert duplicates(args) == {}


# SEED-K2
def test_config_owned_flags_repeated_in_browser_args_are_passed_once(
    tmp_path: pathlib.Path,
) -> None:
    config = make_config(
        tmp_path,
        headless=True,
        sandbox=False,
        lang="de-DE",
        disable_webgl=True,
        browser_args=[
            "--headless=new",
            "--no-sandbox",
            "--lang=de-DE",
            "--disable-webgl",
            "--force-webrtc-ip-handling-policy",
        ],
    )
    args = config()
    assert duplicates(args) == {}
    for flag in ("--headless=new", "--no-sandbox", "--lang=de-DE", "--disable-webgl"):
        assert flag in args


def test_dedupe_keeps_last_value_semantics(tmp_path: pathlib.Path) -> None:
    # Chrome uses the last value of a switch, dedupe must not change which one wins
    config = make_config(
        tmp_path, lang="de-DE", browser_args=["--lang=de-DE", "--lang=fr-FR"]
    )
    langs = [a for a in config() if a.startswith("--lang=")]
    assert langs[-1] == "--lang=de-DE"


class _LaunchCaptured(Exception):
    pass


def _capture_launches(monkeypatch: pytest.MonkeyPatch) -> list[list[str]]:
    launches: list[list[str]] = []

    def fake_start_process(exe, params, is_posix, env=None):  # type: ignore[no-untyped-def]
        launches.append(list(params))
        raise _LaunchCaptured()

    monkeypatch.setattr(util, "_start_process", fake_start_process)
    return launches


# SEED-K3
async def test_start_does_not_append_load_extension_again(
    tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    ext = tmp_path / "ext"
    ext.mkdir()
    (ext / "manifest.json").write_text("{}")
    config = make_config(tmp_path, browser_args=["--mute-audio"])
    config.add_extension(ext)
    launches = _capture_launches(monkeypatch)

    browser = zd.Browser(config)
    for _ in range(2):
        browser.config.host = browser.config.port = None  # launch a fresh process
        with pytest.raises(_LaunchCaptured):
            await browser.start()

    assert len(launches) == 2
    for params in launches:
        assert [p for p in params if p.startswith("--load-extension=")] == [
            "--load-extension=%s" % ext
        ]


# SEED-K4
def test_add_argument_does_not_mutate_callers_list(tmp_path: pathlib.Path) -> None:
    base_args = ["--mute-audio"]
    config = make_config(tmp_path, browser_args=base_args)
    config.add_argument("--window-size=800,600")

    assert base_args == ["--mute-audio"]
    assert "--window-size=800,600" in config()


# SEED-K5
@pytest.mark.parametrize(
    "arg",
    [
        "--disable-features=LanguageDetectionAPI",
        "--accept-lang=de-DE",
        "--enable-features=HeadlessFoo",
        "--load-extension=/opt/language-tools",
        "--disk-cache-dir=/home/lange/cache",
    ],
)
def test_add_argument_accepts_args_that_only_contain_blocked_words(
    tmp_path: pathlib.Path, arg: str
) -> None:
    config = make_config(tmp_path)
    config.add_argument(arg)
    args = config()
    if arg.startswith("--disable-features="):
        merged = [a for a in args if a.startswith("--disable-features=")][0]
        assert "LanguageDetectionAPI" in merged.split("=", 1)[1].split(",")
    else:
        assert arg in args


@pytest.mark.parametrize(
    "arg",
    [
        "--lang=de-DE",
        "--headless",
        "--headless=new",
        "--user-data-dir=/tmp/x",
        "--no-sandbox",
        "--no_sandbox",
        "-headless",
        "--LANG=de",
        "/headless",
    ],
)
def test_add_argument_still_rejects_config_owned_switches(
    tmp_path: pathlib.Path, arg: str
) -> None:
    with pytest.raises(ValueError):
        make_config(tmp_path).add_argument(arg)


# SEED-K5 as seen through Browser.start: the extension path goes through add_argument
async def test_start_accepts_extension_path_containing_blocked_word(
    tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    ext = tmp_path / "headless-language-helper"
    ext.mkdir()
    (ext / "manifest.json").write_text("{}")
    config = make_config(tmp_path)
    config.add_extension(ext)
    launches = _capture_launches(monkeypatch)

    with pytest.raises(_LaunchCaptured):  # repo code raises ValueError instead
        await zd.Browser(config).start()
    assert "--load-extension=%s" % ext in launches[0]
