import asyncio
import math
import os

import pytest

import zendriver
from zendriver import cdp
from zendriver.core.element import Element

print("R46 test imports zendriver from", zendriver.__file__)

PAGE = """<!doctype html><html><body>
<div id="cmt"><!-- c --><i>it</i></div>
<p id="esc">&lt;b&gt;not bold&lt;/b&gt;</p>
<div id="q" title='say "hi"'>q</div>
</body></html>"""


def test_element_is_hashable():
    node = cdp.dom.Node(
        node_id=cdp.dom.NodeId(1),
        backend_node_id=cdp.dom.BackendNodeId(2),
        node_type=1,
        node_name="DIV",
        local_name="div",
        node_value="",
    )
    a = Element(node, None)  # type: ignore[arg-type]
    b = Element(node, None)  # type: ignore[arg-type]
    assert a == b and len({a, b}) == 1


@pytest.fixture
async def browser():
    b = await zendriver.start(headless=True)
    try:
        yield b
    finally:
        await b.stop()


async def test_tab_is_hashable(browser):
    tab = browser.main_tab
    assert {tab: 1}[tab] == 1
    assert len(set(browser.tabs + browser.tabs)) == len(browser.tabs)


async def test_evaluate_unserializable_numbers(browser):
    tab = browser.main_tab
    assert await tab.evaluate("1/0") == math.inf
    assert await tab.evaluate("Math.max()") == -math.inf
    assert math.isnan(await tab.evaluate("NaN"))
    neg_zero = await tab.evaluate("-0")
    assert neg_zero == 0 and math.copysign(1, neg_zero) == -1
    assert await tab.evaluate("2n ** 64n") == 2**64
    assert await tab.evaluate("undefined") is None
    assert await tab.evaluate("0") == 0


@pytest.mark.parametrize("selector", ["#cmt", "#esc", "#q"])
async def test_save_to_dom_keeps_content(browser, tmp_path, selector):
    page = tmp_path / "p.html"
    page.write_text(PAGE)
    tab = await browser.get(page.as_uri())
    js = f"document.querySelector('{selector}').outerHTML"
    before = await tab.evaluate(js)
    el = await tab.select(selector)
    el.attrs["data-x"] = "1"
    await asyncio.wait_for(el.save_to_dom(), 15)
    after = await tab.evaluate(js)
    assert after == before.replace(">", ' data-x="1">', 1)


async def test_async_with_stops_browser():
    async with await zendriver.start(headless=True) as b:
        pid = b._process_pid
    try:
        assert b.stopped
        assert not os.path.exists(f"/proc/{pid}")
    finally:
        await b.stop()
