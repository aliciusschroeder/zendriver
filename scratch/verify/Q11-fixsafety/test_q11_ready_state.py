import asyncio
import time
from typing import Any, Iterator

import pytest

import zendriver as zd


def test_which_copy() -> None:
    print("zendriver imported from:", zd.__file__)


def make_tab(monkeypatch: pytest.MonkeyPatch, states: Iterator[Any]) -> zd.Tab:
    calls: list[Any] = []

    async def evaluate(expression: str, *args: Any, **kwargs: Any) -> Any:
        assert expression == "document.readyState"
        value = next(states)
        calls.append(value)
        return value

    tab = zd.Tab.__new__(zd.Tab)
    monkeypatch.setattr(tab, "evaluate", evaluate)
    tab._q11_calls = calls  # type: ignore[attr-defined]
    return tab


def repeat(*values: Any) -> Iterator[Any]:
    # yield the given values, then keep repeating the last one
    yield from values
    while True:
        yield values[-1]


@pytest.mark.parametrize(
    "until,current",
    [
        ("interactive", "complete"),
        ("loading", "interactive"),
        ("loading", "complete"),
        ("complete", "complete"),
        ("interactive", "interactive"),
        ("loading", "loading"),
    ],
)
async def test_wait_for_ready_state_accepts_later_state(
    monkeypatch: pytest.MonkeyPatch, until: Any, current: str
) -> None:
    tab = make_tab(monkeypatch, repeat(current))
    start = time.monotonic()
    # outer wait_for is only a safety net; its TimeoutError has no message
    result = await asyncio.wait_for(tab.wait_for_ready_state(until, timeout=2), 5)
    assert result is True
    assert time.monotonic() - start < 0.5


async def test_wait_for_ready_state_default_on_complete_page(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    tab = make_tab(monkeypatch, repeat("complete"))
    assert await asyncio.wait_for(tab.wait_for_ready_state(timeout=2), 5) is True


async def test_wait_for_ready_state_still_waits_for_earlier_state(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    tab = make_tab(monkeypatch, repeat("loading", "loading", "interactive"))
    with pytest.raises(asyncio.TimeoutError, match="until complete"):
        await asyncio.wait_for(tab.wait_for_ready_state("complete", timeout=1), 5)

    tab = make_tab(monkeypatch, repeat("loading", "loading", "interactive"))
    assert (
        await asyncio.wait_for(tab.wait_for_ready_state("interactive", timeout=2), 5)
        is True
    )
    assert tab._q11_calls == ["loading", "loading", "interactive"]  # type: ignore[attr-defined]


async def test_wait_for_ready_state_keeps_polling_on_unexpected_value(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    tab = make_tab(monkeypatch, repeat(None, "", "complete"))
    assert (
        await asyncio.wait_for(tab.wait_for_ready_state("interactive", timeout=2), 5)
        is True
    )
