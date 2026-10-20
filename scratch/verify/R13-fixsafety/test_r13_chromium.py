"""R13 regression tests against real headless Chromium."""

import pathlib
import shutil
import tempfile
import typing

import pytest

import zendriver

print("zendriver imported from:", zendriver.__file__)

HTML = """<!doctype html><html><body>
<button id="vis" onclick="window.visClicked=(window.visClicked||0)+1">visible</button>
<button id="hid" style="display:none" onclick="window.hidClicked=(window.hidClicked||0)+1">hidden</button>
<a id="lnk" href="#x" onclick="window.lnkClicks=(window.lnkClicks||0)+1; return false;">link</a>
</body></html>"""


@pytest.fixture
async def tab() -> typing.AsyncIterator[zendriver.Tab]:
    tmp = tempfile.mkdtemp(prefix="r13chr_", dir=str(pathlib.Path(__file__).parent))
    page = pathlib.Path(tmp) / "p.html"
    page.write_text(HTML)
    browser = None
    try:
        browser = await zendriver.start(headless=True)
        t = await browser.get(page.as_uri())
        await t.wait_for("#vis")
        yield t
    finally:
        if browser is not None:
            await browser.stop()
        shutil.rmtree(tmp, ignore_errors=True)


async def test_click_display_none_element_runs_js_click(tab: zendriver.Tab) -> None:
    hid = await tab.query_selector("#hid")
    assert hid is not None
    assert await hid.get_position() is None
    await hid.click()
    assert await tab.evaluate("window.hidClicked") == 1
    with pytest.raises(RuntimeError):
        await hid.screenshot_b64()
    await hid.mouse_click()  # warns, does not raise


async def test_click_linked_source_without_tree(tab: zendriver.Tab) -> None:
    links = await tab.get_all_linked_sources()
    lnk = next(link for link in links if link.get("id") == "lnk")
    assert lnk.tree is None
    await lnk.click()
    await lnk.click()
    assert await tab.evaluate("window.lnkClicks") == 2
    await tab.sleep(0.6)  # let the flash() dot (no pointer-events:none) disappear
    await lnk.mouse_click()
    assert await tab.evaluate("window.lnkClicks") == 3


async def test_visible_click_unchanged(tab: zendriver.Tab) -> None:
    vis = await tab.query_selector("#vis")
    assert vis is not None
    await vis.click()
    await tab.sleep(0.6)  # let the flash() dot (no pointer-events:none) disappear
    await vis.mouse_click()
    assert await tab.evaluate("window.visClicked") == 2
    pos = await vis.get_position(abs=True)
    assert pos is not None and pos.width > 0
