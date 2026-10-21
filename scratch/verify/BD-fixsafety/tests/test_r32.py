import asyncio
import pathlib
import sys

import pytest

import zendriver
from zendriver.core.element import Position

sys.path.insert(0, str(pathlib.Path(__file__).parent))
from pngutil import png_center  # noqa: E402

print("R32 test imports zendriver from", zendriver.__file__)

PAGE = """<!doctype html><html><head><style>body{margin:0}</style></head><body>
<div id=red style="width:300px;height:1200px;background:rgb(255,0,0)"></div>
<div id=blue style="width:300px;height:100px;background:rgb(0,0,255)"></div>
<div id=mir style="width:100px;height:40px;background:rgb(0,255,0);transform:scaleX(-1)"></div>
<div id=rot style="width:100px;height:40px;background:rgb(0,255,0);transform:rotate(90deg)"></div>
<div style="height:2000px"></div></body></html>"""


def test_position_uses_bounding_box_of_quad():
    # quad of a scaleX(-1) element: the points start at the top-right corner
    pos = Position([150, 50, 50, 50, 50, 90, 150, 90])
    assert (pos.left, pos.top, pos.width, pos.height) == (50, 50, 100, 40)
    # quad of a rotate(90deg) element
    pos = Position([520, 120, 520, 320, 480, 320, 480, 120])
    assert (pos.left, pos.top, pos.width, pos.height) == (480, 120, 40, 200)
    assert pos.center == (500, 220)


@pytest.fixture
async def tab(tmp_path):
    page = tmp_path / "page.html"
    page.write_text(PAGE)
    browser = await zendriver.start(headless=True)
    try:
        t = await browser.get(page.as_uri())
        await t.sleep(0.3)
        yield t
    finally:
        await browser.stop()


@pytest.mark.parametrize("selector", ["#mir", "#rot"])
async def test_transformed_element_screenshot_returns(tab, selector):
    el = await tab.select(selector)
    try:
        data = await asyncio.wait_for(el.screenshot_b64(format="png"), 15)
    except asyncio.TimeoutError:
        pytest.fail("Element.screenshot_b64 hung on a transformed element")
    w, h, rgb = png_center(data)
    assert rgb == (0, 255, 0)


async def test_screenshot_of_scrolled_page_captures_element(tab):
    blue = await tab.select("#blue")
    await tab.evaluate("window.scrollTo(0, 1100)")
    await tab.sleep(0.2)
    assert await tab.evaluate("window.scrollY") == 1100
    w, h, rgb = png_center(await asyncio.wait_for(blue.screenshot_b64(format="png"), 15))
    assert (w, h, rgb) == (300, 100, (0, 0, 255))


async def test_save_screenshot_jpg(tab, tmp_path):
    blue = await tab.select("#blue")
    path = await asyncio.wait_for(
        blue.save_screenshot(tmp_path / "x.jpg", format="jpg"), 15
    )
    assert pathlib.Path(path).read_bytes()[:2] == b"\xff\xd8"
