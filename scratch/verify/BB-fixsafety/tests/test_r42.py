import asyncio

import pytest

import zendriver
from zendriver import cdp
from zendriver.core.connection import Connection, ProtocolException

from fakepeer import FakePeer

print("ZENDRIVER IMPORTED FROM", zendriver.__file__)


async def test_a1_4_each_pending_send_gets_its_own_exception() -> None:
    peer = FakePeer()
    for m in ("Target.getTargets", "Target.createTarget", "Browser.getVersion"):
        peer.behaviour[m] = None  # never answer
    conn = Connection(await peer.start())
    try:
        await asyncio.wait_for(conn.aopen(), 5)
        tasks = [
            asyncio.create_task(conn.send(cdp.target.get_targets())),
            asyncio.create_task(
                conn.send(cdp.target.create_target(url="https://secret.example/?token=abc"))
            ),
            asyncio.create_task(conn.send(cdp.browser.get_version())),
        ]
        for _ in range(100):
            if len(peer.received) >= 3:
                break
            await asyncio.sleep(0.01)
        await asyncio.wait_for(conn.aclose(), 5)
        res = await asyncio.wait_for(asyncio.gather(*tasks, return_exceptions=True), 5)
        for r in res:
            print(type(r).__name__, id(r), repr(str(r)))
        assert all(isinstance(r, ProtocolException) for r in res)
        assert res[0] is not res[1] and res[1] is not res[2]
        assert "Target.getTargets" in str(res[0])
        assert "Target.createTarget" not in str(res[0])
        assert "token=abc" not in str(res[2])
        assert str(res[0]).count("command:") == 1
    finally:
        await peer.stop()


@pytest.mark.parametrize("bad", [float("nan"), float("inf")])
async def test_a1_3_nan_params_fail_fast(bad: float) -> None:
    peer = FakePeer()
    conn = Connection(await peer.start())
    try:
        await asyncio.wait_for(conn.aopen(), 5)
        with pytest.raises(ValueError):
            await asyncio.wait_for(
                conn.send(
                    cdp.emulation.set_device_metrics_override(
                        width=100, height=100, device_scale_factor=bad, mobile=False
                    )
                ),
                3,
            )
        assert conn.mapper == {}
        # the connection is still usable
        await asyncio.wait_for(conn.send(cdp.page.reload()), 3)
    finally:
        await conn.aclose()
        await peer.stop()


def _count(conn: Connection, handler: object) -> int:
    return sum(1 for hs in conn.handlers.values() if handler in hs)


def test_a1_7_remove_handlers_with_module_and_handler() -> None:
    conn = Connection("ws://127.0.0.1:1")

    def h(e: object) -> None:
        pass

    def other(e: object) -> None:
        pass

    conn.add_handler(cdp.network, h)
    conn.add_handler(cdp.network.RequestWillBeSent, other)
    n = _count(conn, h)
    assert n > 10
    conn.remove_handlers(cdp.network, h)
    print("event types with h after remove_handlers(cdp.network, h):", _count(conn, h), "of", n)
    assert _count(conn, h) == 0
    assert _count(conn, other) == 1


def test_a1_7_remove_handlers_with_module_only() -> None:
    conn = Connection("ws://127.0.0.1:1")
    conn.add_handler(cdp.network, lambda e: None)
    conn.add_handler(cdp.page.LoadEventFired, lambda e: None)
    conn.remove_handlers(cdp.network)
    left = [t for t, hs in conn.handlers.items() if hs]
    assert left == [cdp.page.LoadEventFired], left


async def test_a1_8_protocol_exception_keeps_error_data() -> None:
    data = "Failed to deserialize params.url - BINDINGS: string value expected at position 12"
    peer = FakePeer()
    peer.behaviour["Page.navigate"] = lambda m: {
        "id": m["id"],
        "error": {"code": -32602, "message": "Invalid parameters", "data": data},
    }
    conn = Connection(await peer.start())
    try:
        with pytest.raises(ProtocolException) as ei:
            await asyncio.wait_for(conn.send(cdp.page.navigate(url=None)), 3)  # type: ignore[arg-type]
        print("str(e):", repr(str(ei.value)))
        assert "Failed to deserialize" in str(ei.value)
        assert ei.value.code == -32602
        assert ei.value.message.startswith("Invalid parameters\ncommand:Page.navigate")
    finally:
        await conn.aclose()
        await peer.stop()
