"""Regression tests for group R25 (autodiscover_targets=False)."""

import asyncio
import os
import shutil

import pytest

import zendriver as zd
from zendriver import cdp

print("\nzendriver imported from", zd.__file__)

needs_chromium = pytest.mark.skipif(shutil.which("chromium") is None, reason="needs chromium")


@pytest.fixture
async def nodisc_browser():
    cfg = zd.Config(headless=True)
    cfg.autodiscover_targets = False
    browser = await asyncio.wait_for(zd.Browser.create(cfg), 60)
    yield browser
    await asyncio.wait_for(browser.stop(), 30)


@needs_chromium
async def test_get_returns_with_autodiscover_off(nodisc_browser):
    # outer wait_for is only a safety net, get() has its own 3 s timeout
    tab = await asyncio.wait_for(
        nodisc_browser.get("data:text/html,<title>one</title>", timeout=3), 20
    )
    assert await tab.evaluate("document.title") == "one"


@needs_chromium
async def test_get_new_tab_returns_with_autodiscover_off(nodisc_browser):
    tab = await asyncio.wait_for(
        nodisc_browser.get("data:text/html,<title>two</title>", new_tab=True, timeout=3),
        20,
    )
    assert await tab.evaluate("document.title") == "two"


@needs_chromium
async def test_close_returns_with_autodiscover_off(nodisc_browser):
    target_id = await nodisc_browser.connection.send(cdp.target.create_target("about:blank"))
    await nodisc_browser.update_targets()
    tab = next(t for t in nodisc_browser.tabs if t.target_id == target_id)
    await asyncio.wait_for(tab.close(), 5)


@needs_chromium
async def test_update_targets_drops_closed_targets(nodisc_browser):
    first = nodisc_browser.tabs[0]
    await nodisc_browser.connection.send(cdp.target.create_target("about:blank"))
    await nodisc_browser.update_targets()
    assert len(nodisc_browser.tabs) == 2
    await nodisc_browser.connection.send(cdp.target.close_target(first.target_id))
    for _ in range(50):
        live = {t.target_id for t in await nodisc_browser._get_targets() if t.type_ == "page"}
        if first.target_id not in live:
            break
        await asyncio.sleep(0.1)
    await nodisc_browser.update_targets()
    assert {t.target_id for t in nodisc_browser.tabs} == live
    assert nodisc_browser.main_tab is not first


async def test_update_targets_prunes_without_chrome():
    """browser-free: update_targets must drop targets chrome no longer lists"""
    b = zd.Browser(zd.Config(browser_executable_path="/bin/true"))
    b.config.host, b.config.port = "127.0.0.1", 1
    try:

        def info(tid):
            return cdp.target.TargetInfo(
                target_id=cdp.target.TargetID(tid), type_="page", title="", url="about:blank",
                attached=False, can_access_opener=False,
            )

        live = [info("A"), info("B")]

        async def get_targets():
            return list(live)

        b._get_targets = get_targets
        await b.update_targets()
        assert [t.target_id for t in b.tabs] == ["A", "B"]
        live.pop(0)
        await b.update_targets()
        assert [t.target_id for t in b.tabs] == ["B"]
        # a late TargetDestroyed for the pruned target must not fail
        await b._handle_target_update(cdp.target.TargetDestroyed(cdp.target.TargetID("A")))
        assert [t.target_id for t in b.tabs] == ["B"]
    finally:
        d = b.config._user_data_dir
        if d and os.path.isdir(d):
            shutil.rmtree(d, ignore_errors=True)
