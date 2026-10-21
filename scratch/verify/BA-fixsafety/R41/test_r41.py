"""Regression tests for group R41 (browser misc). Browser-free except grant_all_permissions."""

import os
import pickle
import shutil
import sys
import types
from typing import Any

import pytest

import zendriver as zd
from zendriver import cdp

print("\nzendriver imported from", zd.__file__)


def _info(tid: str, type_: str = "page", url: str = "about:blank") -> cdp.target.TargetInfo:
    return cdp.target.TargetInfo(
        target_id=cdp.target.TargetID(tid),
        type_=type_,
        title=tid,
        url=url,
        attached=False,
        can_access_opener=False,
    )


@pytest.fixture
async def offline_browser():
    cfg = zd.Config(browser_executable_path="/bin/true", headless=True)
    b = zd.Browser(cfg)
    b.config.host = "127.0.0.1"
    b.config.port = 1
    yield b
    if b.config._user_data_dir and os.path.isdir(b.config._user_data_dir):
        shutil.rmtree(b.config._user_data_dir, ignore_errors=True)


# ---------------- A4.1 iteration ----------------


async def test_iter_with_no_tabs_is_empty(offline_browser):
    assert list(offline_browser) == []
    assert next(iter(offline_browser), None) is None


async def test_iter_with_only_non_page_targets_is_empty(offline_browser):
    offline_browser.targets = [offline_browser._create_tab(_info("sw1", "service_worker"))]
    assert list(offline_browser) == []


async def test_nested_and_parallel_iteration(offline_browser):
    a = offline_browser._create_tab(_info("A"))
    b = offline_browser._create_tab(_info("B"))
    offline_browser.targets = [a, b]
    assert [(x, y) for x in offline_browser for y in offline_browser] == [
        (a, a),
        (a, b),
        (b, a),
        (b, b),
    ]
    assert list(zip(offline_browser, offline_browser)) == [(a, a), (b, b)]


async def test_exhausted_iterator_keeps_raising_stop_iteration(offline_browser):
    offline_browser.targets = [offline_browser._create_tab(_info("A"))]
    it = iter(offline_browser)
    assert len(list(it)) == 1
    assert next(it, None) is None
    assert next(it, None) is None


async def test_reversed_is_an_iterator(offline_browser):
    a = offline_browser._create_tab(_info("A"))
    b = offline_browser._create_tab(_info("B"))
    offline_browser.targets = [a, b]
    assert next(reversed(offline_browser)) is b
    assert list(reversed(offline_browser)) == [b, a]


# ---------------- A4.7 / A4.8 tile_windows ----------------


class _FakeMSSInstance:
    instances: list["_FakeMSSInstance"] = []

    def __init__(self) -> None:
        self.closed = False
        self.monitors = [{"left": 0, "top": 0, "width": 1920, "height": 1080}]
        _FakeMSSInstance.instances.append(self)

    def close(self) -> None:
        self.closed = True

    def __enter__(self) -> "_FakeMSSInstance":
        return self

    def __exit__(self, *a: Any) -> None:
        self.close()


@pytest.fixture
def fake_mss(monkeypatch):
    _FakeMSSInstance.instances = []
    mod = types.ModuleType("mss")
    mod.mss = _FakeMSSInstance  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "mss", mod)
    return _FakeMSSInstance


def _fake_tabs(browser, n):
    tabs = []
    for i in range(n):
        t = browser._create_tab(_info(f"T{i}"))

        async def get_window(i=i):
            return cdp.browser.WindowID(i), cdp.browser.Bounds()

        async def set_window_size(*a, **k):
            return None

        t.get_window = get_window
        t.set_window_size = set_window_size
        tabs.append(t)
    return tabs


async def _noop() -> None:
    return None


async def test_tile_windows_without_tabs_returns_empty_grid(offline_browser, fake_mss):
    offline_browser.update_targets = _noop
    assert await offline_browser.tile_windows() == []


@pytest.mark.parametrize("n", [1, 2, 4])
async def test_tile_windows_uses_the_whole_screen_width(offline_browser, fake_mss, n):
    offline_browser.update_targets = _noop
    grid = await offline_browser.tile_windows(_fake_tabs(offline_browser, n))
    assert len(grid) == n
    right_edge = max(x + w for x, _, w, _ in grid)
    # the windows must cover (almost) the whole width of the screen
    assert right_edge >= 1920 - n * 2, grid


async def test_tile_windows_closes_mss(offline_browser, fake_mss):
    offline_browser.update_targets = _noop
    for _ in range(3):
        await offline_browser.tile_windows(_fake_tabs(offline_browser, 2))
    assert fake_mss.instances
    assert all(m.closed for m in fake_mss.instances)


# ---------------- A12.6 cookie pattern ----------------


def _cookie(name: str, value: str, domain: str = "example.com") -> cdp.network.Cookie:
    return cdp.network.Cookie(
        name=name,
        value=value,
        domain=domain,
        path="/",
        size=len(name) + len(value),
        http_only=False,
        secure=True,
        session=True,
        priority=cdp.network.CookiePriority.MEDIUM,
        source_scheme=cdp.network.CookieSourceScheme.SECURE,
        source_port=443,
    )


@pytest.mark.parametrize("pattern", ["session", "secure", "path", "name", "Medium"])
async def test_cookie_save_matches_only_domain_name_value(offline_browser, tmp_path, pattern):
    jar = offline_browser.cookies

    async def get_all(requests_cookie_format=False):
        return [_cookie("a", "x"), _cookie("session_id", "y")]

    jar.get_all = get_all
    f = tmp_path / "c.dat"
    await jar.save(f, pattern=pattern)
    with f.open("rb") as fh:
        saved = [c.name for c in pickle.load(fh)]
    expected = ["session_id"] if pattern == "session" else []
    assert saved == expected


async def test_cookie_load_matches_only_domain_name_value(offline_browser, tmp_path):
    jar = offline_browser.cookies
    f = tmp_path / "c.dat"
    with f.open("wb") as fh:
        pickle.dump([_cookie("a", "x"), _cookie("b", "y", "cf.example.org")], fh)
    got: list[Any] = []

    async def set_all(cookies):
        got.extend(cookies)

    jar.set_all = set_all
    await jar.load(f, pattern="secure")
    assert got == []
    await jar.load(f, pattern="cf")
    assert [c.name for c in got] == ["b"]
    got.clear()
    await jar.load(f)  # default pattern still loads everything
    assert [c.name for c in got] == ["a", "b"]


# ---------------- A4.6 grant_all_permissions (real chromium) ----------------


@pytest.mark.skipif(shutil.which("chromium") is None, reason="needs chromium")
async def test_grant_all_permissions_succeeds_on_real_chromium():
    import http.server
    import threading

    srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), http.server.SimpleHTTPRequestHandler)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    browser = await zd.start(headless=True)
    try:
        await browser.grant_all_permissions()
        tab = browser.tabs[0]
        await tab.get(f"http://127.0.0.1:{srv.server_address[1]}/")
        # geolocation is a type every chrome knows: it must have been granted
        state = await tab.evaluate(
            "navigator.permissions.query({name:'geolocation'}).then(p => p.state)",
            await_promise=True,
        )
        assert state in ("granted",), state
    finally:
        await browser.stop()
        srv.shutdown()
