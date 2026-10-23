import asyncio
from collections.abc import Coroutine
from typing import Any

import pytest

import zendriver as zd
from zendriver.core import cloudflare as cloudflare_module
from zendriver.core.connection import ProtocolException


class _FakeInputElement:
    def __init__(self) -> None:
        self.attrs: dict[str, str] = {}

    async def update(self) -> "_FakeInputElement":
        return self

    def __await__(self) -> Any:
        return self.update().__await__()


class _FakeChallengeIframe:
    def __init__(self, node_id: int) -> None:
        self.node = zd.cdp.dom.Node(
            node_id=zd.cdp.dom.NodeId(node_id),
            backend_node_id=zd.cdp.dom.BackendNodeId(node_id),
            node_type=1,
            node_name="IFRAME",
            local_name="iframe",
            node_value="",
        )
        self.attrs: dict[str, str] = {}

    @property
    def backend_node_id(self) -> zd.cdp.dom.BackendNodeId:
        return self.node.backend_node_id

    async def scroll_into_view(self) -> None:
        pass


class _HostElementNeverQueried:
    async def query_selector(self, selector: str) -> None:
        raise AssertionError(
            "verify_cf() queried the shadow host for the response input; "
            "it should query the document (tab.query_selector) instead"
        )


async def test_verify_cf_clicks_checkbox_when_input_is_document_level(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    challenge_iframe = _FakeChallengeIframe(node_id=42)

    async def fake_wait_for_challenge(
        _tab: zd.Tab, _timeout: float
    ) -> tuple[Any, Any, Any]:
        return _HostElementNeverQueried(), object(), challenge_iframe

    monkeypatch.setattr(
        cloudflare_module,
        "cf_wait_for_interactive_challenge",
        fake_wait_for_challenge,
    )

    box_model = zd.cdp.dom.BoxModel(
        content=zd.cdp.dom.Quad([0.0, 0.0, 100.0, 0.0, 100.0, 50.0, 0.0, 50.0]),
        padding=zd.cdp.dom.Quad([]),
        border=zd.cdp.dom.Quad([]),
        margin=zd.cdp.dom.Quad([]),
        width=100,
        height=50,
    )

    async def fake_send(cdp_obj: Any, _is_update: bool = False) -> Any:
        next(cdp_obj)
        return box_model

    tab = zd.Tab.__new__(zd.Tab)
    monkeypatch.setattr(tab, "send", fake_send)

    input_element = _FakeInputElement()
    query_selector_calls: list[str] = []

    async def fake_query_selector(selector: str) -> _FakeInputElement | None:
        query_selector_calls.append(selector)
        return input_element

    monkeypatch.setattr(tab, "query_selector", fake_query_selector)

    click_calls: list[tuple[float, float]] = []

    async def fake_mouse_click(x: float, y: float) -> None:
        click_calls.append((x, y))
        input_element.attrs["value"] = "solved"

    monkeypatch.setattr(tab, "mouse_click", fake_mouse_click)

    await cloudflare_module.verify_cf(tab, click_delay=0, timeout=5)

    assert click_calls, "verify_cf() never clicked the checkbox"
    assert query_selector_calls[0] == "input[name=cf-turnstile-response]"


def _box_model(x: float, y: float, width: float, height: float) -> zd.cdp.dom.BoxModel:
    return zd.cdp.dom.BoxModel(
        content=zd.cdp.dom.Quad(
            [x, y, x + width, y, x + width, y + height, x, y + height]
        ),
        padding=zd.cdp.dom.Quad([]),
        border=zd.cdp.dom.Quad([]),
        margin=zd.cdp.dom.Quad([]),
        width=int(width),
        height=int(height),
    )


def _tab_with_challenge_boxes(
    monkeypatch: pytest.MonkeyPatch, boxes: list[Any]
) -> tuple[zd.Tab, _FakeInputElement, list[dict[str, Any]]]:
    """
    a tab on which cf_find_interactive_challenge() finds a challenge iframe
    right away. each time the iframe is measured, the next of boxes is its
    box model, or the exception raised, and the last one once they run out
    """
    challenge_iframe = _FakeChallengeIframe(node_id=42)

    async def fake_find_challenge(_tab: zd.Tab) -> tuple[Any, Any, Any]:
        return _HostElementNeverQueried(), object(), challenge_iframe

    monkeypatch.setattr(
        cloudflare_module, "cf_find_interactive_challenge", fake_find_challenge
    )

    box_model_params: list[dict[str, Any]] = []

    async def fake_send(cdp_obj: Any, _is_update: bool = False) -> Any:
        request = next(cdp_obj)
        assert request["method"] == "DOM.getBoxModel"
        box_model_params.append(request["params"])
        box = boxes.pop(0) if len(boxes) > 1 else boxes[0]
        if isinstance(box, Exception):
            raise box
        return box

    tab = zd.Tab.__new__(zd.Tab)
    monkeypatch.setattr(tab, "send", fake_send)

    input_element = _FakeInputElement()

    async def fake_query_selector(selector: str) -> _FakeInputElement:
        return input_element

    monkeypatch.setattr(tab, "query_selector", fake_query_selector)
    return tab, input_element, box_model_params


async def test_verify_cf_waits_until_challenge_iframe_is_laid_out(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # right after the challenge page loaded, the iframe is in the DOM, but
    # not laid out yet: its content box is 0x0
    tab, input_element, box_model_params = _tab_with_challenge_boxes(
        monkeypatch,
        [_box_model(100, 200, 0, 0), _box_model(100, 200, 300, 65)],
    )
    click_calls: list[tuple[float, float]] = []

    async def fake_mouse_click(x: float, y: float) -> None:
        click_calls.append((x, y))
        input_element.attrs["value"] = "solved"

    monkeypatch.setattr(tab, "mouse_click", fake_mouse_click)

    await asyncio.wait_for(
        cloudflare_module.verify_cf(tab, click_delay=0, timeout=5), 10
    )

    # the checkbox in the laid out iframe, not the 0x0 box at (100, 200)
    assert click_calls == [(100 + 300 * 0.15, 200 + 65 / 2)]
    # the node id changes when the document is fetched again, e.g. by
    # tab.query_selector, the backend node id does not
    assert all(params == {"backendNodeId": 42} for params in box_model_params)


async def test_verify_cf_clicks_where_challenge_iframe_is_now(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    boxes = [_box_model(0, 0, 300, 65)]
    tab, input_element, _ = _tab_with_challenge_boxes(monkeypatch, boxes)
    click_calls: list[tuple[float, float]] = []

    async def fake_mouse_click(x: float, y: float) -> None:
        click_calls.append((x, y))
        if len(click_calls) == 1:
            # the page content above the challenge pushes it down
            boxes[:] = [_box_model(0, 100, 300, 65)]
        else:
            input_element.attrs["value"] = "solved"

    monkeypatch.setattr(tab, "mouse_click", fake_mouse_click)

    await asyncio.wait_for(
        cloudflare_module.verify_cf(tab, click_delay=0, timeout=5), 10
    )

    assert click_calls == [(45, 32.5), (45, 132.5)]


@pytest.mark.parametrize(
    "box_model",
    [_box_model(100, 200, 0, 0), ProtocolException("Could not compute box model.")],
    ids=["0x0", "no box model"],
)
async def test_verify_cf_does_not_click_challenge_iframe_that_is_never_laid_out(
    monkeypatch: pytest.MonkeyPatch, box_model: Any
) -> None:
    tab, _, _ = _tab_with_challenge_boxes(monkeypatch, [box_model])
    click_calls: list[tuple[float, float]] = []

    async def fake_mouse_click(x: float, y: float) -> None:
        click_calls.append((x, y))

    monkeypatch.setattr(tab, "mouse_click", fake_mouse_click)

    assert not await cloudflare_module.cf_is_interactive_challenge_present(
        tab, timeout=1
    )
    with pytest.raises(TimeoutError, match="checkbox not found or not visible"):
        await asyncio.wait_for(
            cloudflare_module.verify_cf(tab, click_delay=0, timeout=1), 5
        )
    assert click_calls == []


async def _never_answered(*args: Any, **kwargs: Any) -> None:
    # a CDP response that never arrives, e.g. while the page shows an alert()
    await asyncio.Event().wait()


def _tab_with_unsolved_challenge(monkeypatch: pytest.MonkeyPatch) -> zd.Tab:
    """a tab on which verify_cf() finds a challenge that never gets solved"""
    challenge_iframe = _FakeChallengeIframe(node_id=42)

    async def fake_wait_for_challenge(
        _tab: zd.Tab, _timeout: float
    ) -> tuple[Any, Any, Any]:
        return _HostElementNeverQueried(), object(), challenge_iframe

    monkeypatch.setattr(
        cloudflare_module,
        "cf_wait_for_interactive_challenge",
        fake_wait_for_challenge,
    )

    box_model = zd.cdp.dom.BoxModel(
        content=zd.cdp.dom.Quad([0.0, 0.0, 100.0, 0.0, 100.0, 50.0, 0.0, 50.0]),
        padding=zd.cdp.dom.Quad([]),
        border=zd.cdp.dom.Quad([]),
        margin=zd.cdp.dom.Quad([]),
        width=100,
        height=50,
    )

    async def fake_send(cdp_obj: Any, _is_update: bool = False) -> Any:
        next(cdp_obj)
        return box_model

    tab = zd.Tab.__new__(zd.Tab)
    monkeypatch.setattr(tab, "send", fake_send)

    input_element = _FakeInputElement()

    async def fake_query_selector(selector: str) -> _FakeInputElement:
        return input_element

    monkeypatch.setattr(tab, "query_selector", fake_query_selector)
    return tab


async def test_cf_is_interactive_challenge_present_is_false_when_cdp_reply_never_arrives(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    tab = zd.Tab.__new__(zd.Tab)
    monkeypatch.setattr(tab, "send", _never_answered)
    loop = asyncio.get_running_loop()
    start_time = loop.time()

    # the outer wait_for is only a safety net so the test can't hang
    present = await asyncio.wait_for(
        cloudflare_module.cf_is_interactive_challenge_present(tab, timeout=1), 5
    )

    assert present is False
    # about the timeout of 1s, with a wide margin
    assert loop.time() - start_time < 2.5


async def test_verify_cf_raises_when_cdp_reply_never_arrives(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    tab = zd.Tab.__new__(zd.Tab)
    monkeypatch.setattr(tab, "send", _never_answered)
    loop = asyncio.get_running_loop()
    start_time = loop.time()

    # the outer wait_for is only a safety net so the test can't hang; its
    # TimeoutError has no message, so `match` tells the two apart
    with pytest.raises(TimeoutError, match="checkbox not found"):
        await asyncio.wait_for(cloudflare_module.verify_cf(tab, timeout=1), 5)

    # about the timeout of 1s, with a wide margin
    assert loop.time() - start_time < 2.5


async def test_verify_cf_raises_when_cdp_reply_never_arrives_during_clicks(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    tab = _tab_with_unsolved_challenge(monkeypatch)
    monkeypatch.setattr(tab, "mouse_click", _never_answered)
    loop = asyncio.get_running_loop()
    start_time = loop.time()

    with pytest.raises(TimeoutError, match="timeout during clicks"):
        await asyncio.wait_for(
            cloudflare_module.verify_cf(tab, click_delay=0, timeout=1), 5
        )

    # about the timeout of 1s, with a wide margin
    assert loop.time() - start_time < 2.5


async def test_verify_cf_click_delay_does_not_overrun_timeout(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    tab = _tab_with_unsolved_challenge(monkeypatch)

    async def fake_mouse_click(x: float, y: float) -> None:
        pass

    monkeypatch.setattr(tab, "mouse_click", fake_mouse_click)
    loop = asyncio.get_running_loop()
    start_time = loop.time()

    # the safety net is shorter than click_delay
    with pytest.raises(TimeoutError, match="timeout during clicks"):
        await asyncio.wait_for(
            cloudflare_module.verify_cf(tab, click_delay=4, timeout=1), 3
        )

    # about the timeout of 1s, with a wide margin
    assert loop.time() - start_time < 2.5


@pytest.mark.parametrize("phase", ["find", "click"])
@pytest.mark.parametrize("fails", [False, True], ids=["found", "failed"])
async def test_cf_bounds_keep_a_cancel_that_arrives_with_the_answer(
    monkeypatch: pytest.MonkeyPatch, phase: str, fails: bool
) -> None:
    attempt_started = asyncio.Event()
    answer: asyncio.Future[Any] = asyncio.get_running_loop().create_future()

    async def wait_for_answer(*args: Any, **kwargs: Any) -> Any:
        attempt_started.set()
        return await answer

    call: Coroutine[Any, Any, object]
    found: Any
    if phase == "find":
        tab = zd.Tab.__new__(zd.Tab)
        monkeypatch.setattr(
            cloudflare_module, "cf_find_interactive_challenge", wait_for_answer
        )
        call = cloudflare_module.cf_is_interactive_challenge_present(tab, timeout=5)
        found = (object(), object(), _FakeInputElement())
    else:
        tab = _tab_with_unsolved_challenge(monkeypatch)
        monkeypatch.setattr(cloudflare_module, "_cf_click_challenge", wait_for_answer)
        call = cloudflare_module.verify_cf(tab, timeout=5)
        found = None
    task = asyncio.create_task(call)
    await asyncio.wait_for(attempt_started.wait(), 5)

    # the CDP answer arrives in the loop iteration in which the caller is
    # cancelled. before python 3.12, asyncio.wait_for then returned the
    # answer (or raised its exception) instead
    if fails:
        answer.set_exception(RuntimeError("the attempt failed"))
    else:
        answer.set_result(found)
    task.cancel()
    await asyncio.wait({task}, timeout=5)

    assert task.cancelled(), task.exception() or task.result()
