"""Regression tests for R20: Element.send_keys(str) must send Enter as '\r' in CHAR mode."""

import asyncio
import pathlib
import shutil

import pytest

import zendriver as zd
from zendriver import KeyEvents, KeyPressEvent, SpecialKeys

print("zendriver imported from", zd.__file__)


def test_print_import_path() -> None:
    print("zendriver imported from", zd.__file__)


def test_from_text_char_mode_sends_enter_as_carriage_return() -> None:
    payloads = KeyEvents.from_text("a\nb\rc", KeyPressEvent.CHAR)
    assert [p["type_"] for p in payloads] == ["char"] * 5
    assert [p["text"] for p in payloads] == ["a", "\r", "b", "\r", "c"]


def test_special_enter_char_event_uses_carriage_return() -> None:
    (payload,) = KeyEvents(SpecialKeys.ENTER).to_cdp_events(KeyPressEvent.CHAR)
    assert payload["text"] == "\r"
    # TAB and SPACE stay unchanged
    (tab,) = KeyEvents(SpecialKeys.TAB).to_cdp_events(KeyPressEvent.CHAR)
    (space,) = KeyEvents(SpecialKeys.SPACE).to_cdp_events(KeyPressEvent.CHAR)
    assert tab["text"] == "\t" and space["text"] == " "


def test_char_mode_matches_down_and_up_text_for_enter() -> None:
    char_text = KeyEvents.from_text("\n", KeyPressEvent.CHAR)[0]["text"]
    down_up = KeyEvents.from_text("\n", KeyPressEvent.DOWN_AND_UP)
    assert {p["text"] for p in down_up} == {"\r"}
    assert char_text == "\r"


PAGE = """<!doctype html><html><body>
<form id="f" onsubmit="event.preventDefault(); window.submits=(window.submits||0)+1;">
<input id="inp" type="text"><button type="submit">go</button></form>
<textarea id="ta"></textarea>
<script>window.submits=0;</script>
</body></html>"""


@pytest.mark.skipif(shutil.which("chromium") is None, reason="needs chromium on PATH")
async def test_send_keys_newlines_reach_chromium(tmp_path: pathlib.Path) -> None:
    page = tmp_path / "page.html"
    page.write_text(PAGE)
    browser = await zd.start(headless=True)
    try:
        tab = await browser.get(page.as_uri())
        await tab.wait_for_ready_state("complete")
        ta = await tab.select("#ta")
        await asyncio.wait_for(ta.send_keys("line1\nline2\rline3"), 30)
        assert (
            await tab.evaluate("document.getElementById('ta').value")
            == "line1\nline2\nline3"
        )

        inp = await tab.select("#inp")
        await asyncio.wait_for(inp.send_keys("query\n"), 30)
        await asyncio.sleep(0.2)
        assert await tab.evaluate("window.submits") == 1
        assert await tab.evaluate("document.getElementById('inp').value") == "query"
    finally:
        await browser.stop()
