import asyncio

import pytest

import zendriver
from zendriver import cdp
from zendriver.core.connection import ProtocolException

print("R33 test imports zendriver from", zendriver.__file__)

PAGE = """<!doctype html><html><body>
<div id=box><span>child</span></div>
<input id=inp value="input text">
<input id=mail type=email value="a@b.cd">
<textarea id=ta>some text</textarea>
</body></html>"""


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


async def value_of(tab, id_):
    return await tab.evaluate(f"document.getElementById('{id_}').value")


async def test_apply_raises_on_js_exception(tab):
    box = await tab.select("#box")
    with pytest.raises(ProtocolException):
        await asyncio.wait_for(box.apply('(e) => { throw new Error("boom") }'), 15)


async def test_apply_raises_on_rejected_promise(tab):
    box = await tab.select("#box")
    with pytest.raises(ProtocolException):
        await asyncio.wait_for(
            box.apply('async (e) => { throw new Error("boom") }', await_promise=True), 15
        )


async def test_apply_still_returns_values(tab):
    box = await tab.select("#box")
    assert await box.apply("(e) => e.id") == "box"
    assert await box.apply("(e) => { }") is None
    assert await box.apply("(e) => 0") == 0


async def test_apply_return_by_value_false_returns_remote_handle(tab):
    box = await tab.select("#box")
    handle = await box.apply("(e) => e.firstElementChild", return_by_value=False)
    assert handle.object_id is not None
    tag, _ = await tab.send(
        cdp.runtime.call_function_on(
            "function () { return this.tagName }",
            object_id=handle.object_id,
            return_by_value=True,
        )
    )
    assert tag.value == "SPAN"


async def test_clear_input_textarea(tab):
    ta = await tab.select("#ta")
    await asyncio.wait_for(ta.clear_input(), 15)
    assert await value_of(tab, "ta") == ""


async def test_clear_input_by_deleting_textarea(tab):
    ta = await tab.select("#ta")
    await asyncio.wait_for(ta.clear_input_by_deleting(), 15)
    assert await value_of(tab, "ta") == ""


async def test_clear_input_still_works_on_input(tab):
    inp = await tab.select("#inp")
    await asyncio.wait_for(inp.clear_input(), 15)
    assert await value_of(tab, "inp") == ""
    mail = await tab.select("#mail")
    await asyncio.wait_for(mail.clear_input_by_deleting(), 15)
    assert await value_of(tab, "mail") == ""
