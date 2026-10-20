"""
Q2 regression tests: polling methods must honour their timeout even when a CDP
reply never arrives (page blocked by alert() / busy JS).  Browser-free: the CDP
layer is replaced with instance patches, like the #291 wait_for_ready_state test.

Every call is wrapped in an OUTER asyncio.wait_for(…, SAFETY) whose TimeoutError
has no message, so `match=` tells the method's own timeout apart from the net.
"""

from __future__ import annotations

import asyncio
import time
from typing import Any

import pytest

import zendriver as zd
from zendriver.core import cloudflare as cloudflare_module

SAFETY = 6
SLACK = 1.0  # seconds allowed past the requested timeout


def test_print_which_copy() -> None:
    print("\nzendriver imported from", zd.__file__)


async def _hang(*args: Any, **kwargs: Any) -> Any:
    # a CDP response that never arrives
    await asyncio.Event().wait()


async def _noop(*args: Any, **kwargs: Any) -> None:
    return None


def _tab(monkeypatch: pytest.MonkeyPatch) -> zd.Tab:
    tab = zd.Tab.__new__(zd.Tab)
    # Connection.sleep() calls update_target(); keep it local
    monkeypatch.setattr(tab, "update_target", _noop)
    return tab


async def _timed(coro: Any) -> tuple[Any, float]:
    t0 = time.monotonic()
    result = await asyncio.wait_for(coro, SAFETY)
    return result, time.monotonic() - t0


# ---------------------------------------------------------------- find/select


@pytest.mark.parametrize(
    "method, patch, args, match",
    [
        ("select", "query_selector", ("#x",), "selector: '#x'"),
        ("find", "find_element_by_text", ("x",), "text: 'x'"),
        ("find_all", "find_elements_by_text", ("x",), "any element with text: 'x'"),
        ("select_all", "query_selector_all", ("#x",), "any element with selector"),
    ],
)
async def test_find_select_time_out_when_cdp_hangs(
    monkeypatch: pytest.MonkeyPatch, method: str, patch: str, args: tuple, match: str
) -> None:
    tab = _tab(monkeypatch)
    monkeypatch.setattr(tab, patch, _hang)
    t0 = time.monotonic()
    with pytest.raises(asyncio.TimeoutError, match=match):
        await asyncio.wait_for(getattr(tab, method)(*args, timeout=1), SAFETY)
    assert time.monotonic() - t0 < 1 + SLACK


async def test_select_include_frames_times_out_when_get_frames_hangs(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    tab = _tab(monkeypatch)

    async def empty(*a: Any, **k: Any) -> list:
        return []

    monkeypatch.setattr(tab, "query_selector_all", empty)
    monkeypatch.setattr(tab, "get_frames", _hang)
    with pytest.raises(asyncio.TimeoutError, match="selector: '#x'"):
        await asyncio.wait_for(tab.select("#x", timeout=1, include_frames=True), SAFETY)


@pytest.mark.parametrize("kw, patch", [("selector", "query_selector"), ("text", "find_element_by_text")])
async def test_wait_for_times_out_when_cdp_hangs(
    monkeypatch: pytest.MonkeyPatch, kw: str, patch: str
) -> None:
    tab = _tab(monkeypatch)
    monkeypatch.setattr(tab, patch, _hang)
    t0 = time.monotonic()
    with pytest.raises(asyncio.TimeoutError, match="time ran out while waiting"):
        await asyncio.wait_for(tab.wait_for(**{kw: "#x"}, timeout=1), SAFETY)
    assert time.monotonic() - t0 < 1 + SLACK


async def test_tab_call_times_out_when_cdp_hangs(monkeypatch: pytest.MonkeyPatch) -> None:
    tab = _tab(monkeypatch)
    monkeypatch.setattr(tab, "query_selector", _hang)
    monkeypatch.setattr(tab, "find_element_by_text", _hang)
    with pytest.raises(asyncio.TimeoutError, match="time ran out while waiting"):
        await asyncio.wait_for(tab(selector="#x", timeout=1), SAFETY)


# ---- behaviour that must be preserved (passes before and after the fix) ----


async def test_select_timeout_zero_still_makes_one_attempt(monkeypatch: pytest.MonkeyPatch) -> None:
    tab = _tab(monkeypatch)
    sentinel = object()

    async def qs(*a: Any, **k: Any) -> Any:
        await asyncio.sleep(0.05)  # a real round trip takes a few ms
        return sentinel

    monkeypatch.setattr(tab, "query_selector", qs)
    assert await asyncio.wait_for(tab.select("#x", timeout=0), SAFETY) is sentinel
    monkeypatch.setattr(tab, "find_element_by_text", qs)
    assert await asyncio.wait_for(tab.find("x", timeout=0), SAFETY) is sentinel
    assert await asyncio.wait_for(tab.wait_for(selector="#x", timeout=0), SAFETY) is sentinel


async def test_select_timeout_zero_miss_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    tab = _tab(monkeypatch)
    calls = 0

    async def qs(*a: Any, **k: Any) -> None:
        nonlocal calls
        calls += 1

    monkeypatch.setattr(tab, "query_selector", qs)
    with pytest.raises(asyncio.TimeoutError, match="selector: '#x'"):
        await asyncio.wait_for(tab.select("#x", timeout=0), SAFETY)
    assert calls == 1


async def test_select_finds_element_that_appears_later(monkeypatch: pytest.MonkeyPatch) -> None:
    tab = _tab(monkeypatch)
    sentinel = object()
    t0 = time.monotonic()

    async def qs(*a: Any, **k: Any) -> Any:
        return sentinel if time.monotonic() - t0 > 0.7 else None

    monkeypatch.setattr(tab, "query_selector", qs)
    assert await asyncio.wait_for(tab.select("#x", timeout=3), SAFETY) is sentinel


# ---------------------------------------------------------------------- xpath


async def test_xpath_returns_empty_when_cdp_hangs(monkeypatch: pytest.MonkeyPatch) -> None:
    tab = _tab(monkeypatch)
    monkeypatch.setattr(tab, "send", _hang)
    result, dt = await _timed(tab.xpath("//x", timeout=1))
    assert result == []
    assert dt < 1 + SLACK


async def test_xpath_timeout_zero_makes_one_attempt(monkeypatch: pytest.MonkeyPatch) -> None:
    tab = _tab(monkeypatch)
    sentinel = object()
    monkeypatch.setattr(tab, "send", _noop)
    monkeypatch.setattr(tab, "disable_dom_agent", _noop)

    async def find_all(*a: Any, **k: Any) -> list:
        return [sentinel]

    monkeypatch.setattr(tab, "find_all", find_all)
    assert await asyncio.wait_for(tab.xpath("//x", timeout=0), SAFETY) == [sentinel]


async def test_xpath_does_not_busy_loop(monkeypatch: pytest.MonkeyPatch) -> None:
    tab = _tab(monkeypatch)
    attempts = 0
    monkeypatch.setattr(tab, "send", _noop)
    monkeypatch.setattr(tab, "disable_dom_agent", _noop)

    async def find_all(*a: Any, **k: Any) -> list:
        nonlocal attempts
        attempts += 1
        raise asyncio.TimeoutError("not found")

    monkeypatch.setattr(tab, "find_all", find_all)
    result, dt = await _timed(tab.xpath("//x", timeout=1))
    assert result == []
    assert dt < 1 + SLACK
    assert attempts <= 10, f"{attempts} attempts in 1 s: xpath spins without sleeping"


# ----------------------------------------------------------------- cloudflare


async def test_cf_is_interactive_challenge_present_false_when_cdp_hangs(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    tab = _tab(monkeypatch)
    monkeypatch.setattr(tab, "send", _hang)
    result, dt = await _timed(cloudflare_module.cf_is_interactive_challenge_present(tab, timeout=1))
    assert result is False
    assert dt < 1 + SLACK


async def test_verify_cf_raises_when_cdp_hangs(monkeypatch: pytest.MonkeyPatch) -> None:
    tab = _tab(monkeypatch)
    monkeypatch.setattr(tab, "send", _hang)
    t0 = time.monotonic()
    # builtin TimeoutError, as documented (matters on 3.10 where they differ)
    with pytest.raises(TimeoutError, match="Cloudflare"):
        await asyncio.wait_for(tab.verify_cf(timeout=1), SAFETY)
    assert time.monotonic() - t0 < 1 + SLACK


class _FakeInput:
    def __init__(self) -> None:
        self.attrs: dict[str, str] = {}

    async def update(self) -> "_FakeInput":
        return self

    def __await__(self) -> Any:
        return self.update().__await__()


class _FakeIframe:
    def __init__(self) -> None:
        self.node = zd.cdp.dom.Node(
            node_id=zd.cdp.dom.NodeId(42),
            backend_node_id=zd.cdp.dom.BackendNodeId(42),
            node_type=1,
            node_name="IFRAME",
            local_name="iframe",
            node_value="",
        )

    async def scroll_into_view(self) -> None:
        pass


def _found_challenge(monkeypatch: pytest.MonkeyPatch, tab: zd.Tab) -> None:
    iframe = _FakeIframe()

    async def fake_wait(_tab: Any, _timeout: float) -> tuple[Any, Any, Any]:
        return object(), object(), iframe

    monkeypatch.setattr(cloudflare_module, "cf_wait_for_interactive_challenge", fake_wait)
    box = zd.cdp.dom.BoxModel(
        content=zd.cdp.dom.Quad([0.0, 0.0, 100.0, 0.0, 100.0, 50.0, 0.0, 50.0]),
        padding=zd.cdp.dom.Quad([]),
        border=zd.cdp.dom.Quad([]),
        margin=zd.cdp.dom.Quad([]),
        width=100,
        height=50,
    )

    async def fake_send(cdp_obj: Any, _is_update: bool = False) -> Any:
        next(cdp_obj)
        return box

    monkeypatch.setattr(tab, "send", fake_send)


async def test_verify_cf_click_delay_does_not_overrun_timeout(monkeypatch: pytest.MonkeyPatch) -> None:
    tab = _tab(monkeypatch)
    _found_challenge(monkeypatch, tab)
    inp = _FakeInput()  # never gets a value: unsolvable

    async def qs(*a: Any, **k: Any) -> Any:
        return inp

    monkeypatch.setattr(tab, "query_selector", qs)
    monkeypatch.setattr(tab, "mouse_click", _noop)
    t0 = time.monotonic()
    with pytest.raises(TimeoutError):
        await asyncio.wait_for(tab.verify_cf(timeout=1, click_delay=4), SAFETY)
    assert time.monotonic() - t0 < 1 + SLACK


async def test_verify_cf_click_phase_hang_is_bounded(monkeypatch: pytest.MonkeyPatch) -> None:
    tab = _tab(monkeypatch)
    _found_challenge(monkeypatch, tab)
    inp = _FakeInput()
    calls = 0

    async def qs(*a: Any, **k: Any) -> Any:
        nonlocal calls
        calls += 1
        if calls > 1:  # renderer stops answering after the first lookup
            await asyncio.Event().wait()
        return inp

    monkeypatch.setattr(tab, "query_selector", qs)
    monkeypatch.setattr(tab, "mouse_click", _noop)
    t0 = time.monotonic()
    with pytest.raises(TimeoutError):
        await asyncio.wait_for(tab.verify_cf(timeout=1, click_delay=0.1), SAFETY)
    assert time.monotonic() - t0 < 1 + SLACK


async def test_verify_cf_solves_quickly(monkeypatch: pytest.MonkeyPatch) -> None:
    """preserved behaviour: a solvable challenge returns normally"""
    tab = _tab(monkeypatch)
    _found_challenge(monkeypatch, tab)
    inp = _FakeInput()

    async def qs(*a: Any, **k: Any) -> Any:
        return inp

    async def click(*a: Any, **k: Any) -> None:
        inp.attrs["value"] = "solved"

    monkeypatch.setattr(tab, "query_selector", qs)
    monkeypatch.setattr(tab, "mouse_click", click)
    await asyncio.wait_for(tab.verify_cf(timeout=2, click_delay=0.1), SAFETY)


# ---- preserved behaviour: the attempt made at/after the deadline still counts ----


@pytest.mark.parametrize(
    "method, patch, timeout, appears_at",
    [
        ("select", "query_selector", 0.5, 0.3),
        ("select", "query_selector", 1, 0.7),
        ("find", "find_element_by_text", 1, 0.7),
    ],
)
async def test_element_appearing_before_deadline_is_found(
    monkeypatch: pytest.MonkeyPatch, method: str, patch: str, timeout: float, appears_at: float
) -> None:
    tab = _tab(monkeypatch)
    sentinel = object()
    t0 = time.monotonic()

    async def lookup(*a: Any, **k: Any) -> Any:
        await asyncio.sleep(0.005)  # round trip
        return sentinel if time.monotonic() - t0 > appears_at else None

    monkeypatch.setattr(tab, patch, lookup)
    assert await asyncio.wait_for(getattr(tab, method)("x", timeout=timeout), SAFETY) is sentinel


async def test_wait_for_keeps_element_found_just_before_deadline(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    tab = _tab(monkeypatch)
    sentinel = object()
    t0 = time.monotonic()

    async def qs(*a: Any, **k: Any) -> Any:
        await asyncio.sleep(0.005)
        return sentinel if time.monotonic() - t0 > 0.3 else None

    monkeypatch.setattr(tab, "query_selector", qs)
    # found by the attempt at ~0.5 s; wait_for then sleeps 0.5 s before returning
    assert await asyncio.wait_for(tab.wait_for(selector="#x", timeout=1), SAFETY) is sentinel
