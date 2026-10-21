"""Round-2 edge probes for the Q2 fix (browser-free)."""

import asyncio
import sys
import time
from typing import Any

import zendriver as zd
from zendriver.core.connection import ProtocolException


async def noop(*a: Any, **k: Any) -> None:
    return None


async def never(*a: Any, **k: Any) -> None:
    await asyncio.Event().wait()


def new_tab() -> zd.Tab:
    tab = zd.Tab.__new__(zd.Tab)
    tab.update_target = noop  # type: ignore
    return tab


async def run(name: str, coro: Any, net: float = 6.0) -> None:
    t0 = time.monotonic()
    try:
        r = await asyncio.wait_for(coro, net)
        print(f"[{name}] -> {r!r} in {time.monotonic() - t0:.2f}s")
    except BaseException as e:  # noqa
        print(f"[{name}] {type(e).__name__}({str(e)!r}) in {time.monotonic() - t0:.2f}s")


async def main() -> None:
    print(sys.version.split()[0], zd.__file__)
    element = object()

    async def hit(*a: Any, **k: Any) -> object:
        return element

    async def hit_all(*a: Any, **k: Any) -> list[object]:
        return [element]

    # E1 timeout=None with an immediate hit (base returned the element)
    for meth in ("select", "find", "find_all", "select_all", "wait_for"):
        tab = new_tab()
        tab.query_selector = hit  # type: ignore
        tab.find_element_by_text = hit  # type: ignore
        tab.query_selector_all = hit_all  # type: ignore
        tab.find_elements_by_text = hit_all  # type: ignore
        await run(f"E1 {meth} timeout=None hit", getattr(tab, meth)("x", timeout=None))

    # E3 wait_for selector misses, text attempt after deadline takes 0.6s
    tab = new_tab()

    async def miss(*a: Any, **k: Any) -> None:
        await asyncio.sleep(0.01)
        return None

    async def slow_text(*a: Any, **k: Any) -> object:
        await asyncio.sleep(0.6)
        return element

    tab.query_selector = miss  # type: ignore
    tab.find_element_by_text = slow_text  # type: ignore
    await run("E3 wait_for(sel miss, text hit 0.6s) timeout=1", tab.wait_for("#x", "t", timeout=1))

    # E5 ProtocolException passes through unchanged
    tab = new_tab()

    async def boom(*a: Any, **k: Any) -> None:
        raise ProtocolException("boom")

    tab.query_selector = boom  # type: ignore
    await run("E5 select ProtocolException", tab.select("#x", timeout=1))

    # E6 builtin TimeoutError from the lookup itself (e.g. OS/socket timeout)
    tab = new_tab()

    async def os_timeout(*a: Any, **k: Any) -> None:
        raise TimeoutError("socket timed out")

    tab.query_selector = os_timeout  # type: ignore
    await run("E6 select inner builtin TimeoutError", tab.select("#x", timeout=1))

    # E7 xpath slow single attempt (0.7s) with timeout=0 and timeout=0.1
    for t in (0, 0.1, 1):
        tab = new_tab()
        tab.send = noop  # type: ignore

        async def slow_find_all(*a: Any, **k: Any) -> list[object]:
            await asyncio.sleep(0.7)
            return [element]

        tab.find_all = slow_find_all  # type: ignore
        await run(f"E7 xpath slow attempt 0.7s timeout={t}", tab.xpath("//x", timeout=t))

    # E8 select timeout=0.001 slow attempt 0.7s vs timeout=0
    for t in (0, 0.001):
        tab = new_tab()

        async def slow_hit(*a: Any, **k: Any) -> object:
            await asyncio.sleep(0.7)
            return element

        tab.query_selector = slow_hit  # type: ignore
        await run(f"E8 select slow attempt 0.7s timeout={t}", tab.select("#x", timeout=t))

    # E9 two concurrent blocked calls on one tab
    tab = new_tab()
    tab.send = never  # type: ignore
    t0 = time.monotonic()
    try:
        res = await asyncio.wait_for(asyncio.gather(
            tab.select("#a", timeout=1), tab.xpath("//a", timeout=1), return_exceptions=True
        ), 5)
    except asyncio.TimeoutError:
        res = ["SAFETY NET"]
    print(f"[E9 concurrent] {[type(r).__name__ for r in res]} in {time.monotonic() - t0:.2f}s")

    # E10 tasks left behind
    await asyncio.sleep(0.1)
    others = [t for t in asyncio.all_tasks() if t is not asyncio.current_task()]
    print("[E10] leftover tasks:", len(others))


asyncio.run(main())
