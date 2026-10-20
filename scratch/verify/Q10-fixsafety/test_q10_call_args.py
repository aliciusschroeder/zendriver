"""Regression tests for Q10: Tab.__call__ must forward text/selector to the
matching wait_for parameters (it passed them positionally in swapped order)."""

import asyncio
import os
import shutil
import tempfile
from typing import Any

import pytest

import zendriver
from zendriver.core.tab import Tab

print("zendriver imported from:", zendriver.__file__)


class _Sentinel:
    def __init__(self, kind: str, arg: str):
        self.kind = kind
        self.arg = arg

    def __repr__(self) -> str:
        return f"<found by {self.kind}({self.arg!r})>"


def _make_tab() -> tuple[Tab, list[tuple[str, str]]]:
    """A Tab that never connects; DOM primitives are replaced on the instance.

    query_selector only matches the CSS selector '#p1'; find_element_by_text only
    matches the text 'Hello needle'.  The real Tab.wait_for and Tab.__call__ run.
    """
    tab = Tab("ws://127.0.0.1:9/devtools/page/fake", target=None)
    calls: list[tuple[str, str]] = []

    async def query_selector(selector: str, _node: Any = None) -> Any:
        calls.append(("query_selector", selector))
        return _Sentinel("css", selector) if selector == "#p1" else None

    async def find_element_by_text(text: str, *a: Any, **kw: Any) -> Any:
        calls.append(("find_element_by_text", text))
        return _Sentinel("text", text) if "Hello needle" in text else None

    async def sleep(t: float = 0.25) -> None:
        await asyncio.sleep(0.01)

    tab.query_selector = query_selector  # type: ignore[method-assign]
    tab.find_element_by_text = find_element_by_text  # type: ignore[method-assign]
    tab.sleep = sleep  # type: ignore[method-assign]
    return tab, calls


async def test_call_text_kwarg_searches_by_text() -> None:
    tab, calls = _make_tab()
    found = await asyncio.wait_for(tab(text="Hello needle", timeout=0.3), 10)
    assert isinstance(found, _Sentinel) and found.kind == "text", (found, calls)
    assert ("query_selector", "Hello needle") not in calls, calls


async def test_call_selector_kwarg_queries_css() -> None:
    tab, calls = _make_tab()
    found = await asyncio.wait_for(tab(selector="#p1", timeout=0.3), 10)
    assert isinstance(found, _Sentinel) and found.kind == "css", (found, calls)
    assert ("find_element_by_text", "#p1") not in calls, calls


async def test_call_first_positional_is_text() -> None:
    # signature is __call__(text, selector, timeout): tab("...") is a text search
    tab, calls = _make_tab()
    found = await asyncio.wait_for(tab("Hello needle", timeout=0.3), 10)
    assert isinstance(found, _Sentinel) and found.kind == "text", (found, calls)


async def test_call_timeout_still_raises() -> None:
    tab, calls = _make_tab()
    with pytest.raises(asyncio.TimeoutError):
        await asyncio.wait_for(tab(text="not on the page", timeout=0.2), 10)
    with pytest.raises(asyncio.TimeoutError):
        await asyncio.wait_for(tab(selector="#nope", timeout=0.2), 10)


@pytest.mark.skipif(
    shutil.which("chromium") is None and shutil.which("chrome") is None,
    reason="no chromium on PATH",
)
async def test_call_text_real_chromium() -> None:
    udd = tempfile.mkdtemp(prefix="q10-udd-")
    browser = await zendriver.start(headless=True, user_data_dir=udd)
    try:
        tab = await browser.get(
            "data:text/html,<p id='p1'>Hello needle world</p><button>Sign up!</button>"
        )
        el = await asyncio.wait_for(tab(text="Hello needle", timeout=3), 30)
        assert el.tag_name == "p", el
        el2 = await asyncio.wait_for(tab(text="Sign up!", timeout=3), 30)
        assert el2.tag_name == "button", el2
        el3 = await asyncio.wait_for(tab(selector="#p1", timeout=3), 30)
        assert el3.tag_name == "p" and el3.attrs.get("id") == "p1", el3
    finally:
        await browser.stop()
        shutil.rmtree(udd, ignore_errors=True)
