"""edge cases for the prototype: behaviour a caller could notice"""

import asyncio
import gc
from typing import Any

import pytest

from test_r22_session_attach import evaluate, peer  # noqa: F401

from zendriver import cdp
from zendriver.core.connection import ProtocolException


async def test_concurrent_first_sends_one_cancelled(peer: Any) -> None:  # noqa: F811
    fake, browser_connection, tab = peer
    fake.attach_delay = 0.3
    first = asyncio.ensure_future(tab.send(evaluate()))
    others = [asyncio.ensure_future(tab.send(evaluate())) for _ in range(4)]
    await asyncio.sleep(0.1)
    first.cancel()
    results = await asyncio.wait_for(asyncio.gather(*others), 5)
    assert all(r[0].value == 2 for r in results)
    await asyncio.wait_for(tab.aclose(), 5)
    await asyncio.sleep(0.1)
    print("attached", fake.attached, "detached", fake.detached)
    assert sorted(fake.attached) == sorted(fake.detached)


async def test_aclose_before_late_attach_reply(peer: Any) -> None:  # noqa: F811
    fake, browser_connection, tab = peer
    fake.attach_delay = 0.3
    with pytest.raises(asyncio.TimeoutError):
        await asyncio.wait_for(tab.send(evaluate()), 0.1)
    await asyncio.wait_for(tab.aclose(), 5)
    await asyncio.sleep(0.5)
    print(
        "after aclose + late reply: session_id",
        tab.session_id,
        "sessions",
        list(browser_connection._sessions),
        "closed",
        tab.closed,
        "attached",
        fake.attached,
        "detached",
        fake.detached,
    )


async def test_attach_error_is_raised_and_retried(peer: Any) -> None:  # noqa: F811
    fake, browser_connection, tab = peer
    original = fake.attach

    async def failing_attach(ws: Any, message: dict[str, Any]) -> None:
        fake.burst(
            ws,
            {"id": message["id"], "error": {"code": -32602, "message": "No target with given id found"}},
        )

    fake.attach = failing_attach
    with pytest.raises(ProtocolException, match="No target"):
        await asyncio.wait_for(tab.send(evaluate()), 5)
    fake.attach = original
    result = await asyncio.wait_for(tab.send(evaluate()), 5)
    assert result[0].value == 2


async def test_browser_closed_during_attach(peer: Any) -> None:  # noqa: F811
    fake, browser_connection, tab = peer
    fake.attach_delay = 5
    task = asyncio.ensure_future(tab.send(evaluate()))
    await asyncio.sleep(0.1)
    task2 = asyncio.ensure_future(tab.send(evaluate()))
    await asyncio.sleep(0.1)
    task.cancel()
    await asyncio.wait_for(browser_connection.aclose(), 5)
    with pytest.raises(Exception) as info:
        await asyncio.wait_for(task2, 5)
    print("second caller after browser close:", type(info.value).__name__, info.value)
    gc.collect()
