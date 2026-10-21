"""Edge-case probes for the Q2 timeout-bounds fix (browser-free)."""

import asyncio
import math
import sys
import time
from typing import Any

import zendriver as zd


async def never(*a: Any, **k: Any) -> None:
    await asyncio.Event().wait()


async def noop(*a: Any, **k: Any) -> None:
    return None


def new_tab() -> zd.Tab:
    return zd.Tab.__new__(zd.Tab)


async def run(name: str, coro: Any, net: float = 4.0) -> None:
    t0 = time.monotonic()
    try:
        r = await asyncio.wait_for(coro, net)
        print(f"[{name}] -> {r!r} in {time.monotonic() - t0:.2f}s")
    except asyncio.TimeoutError as e:
        print(
            f"[{name}] TimeoutError({str(e)!r}) in {time.monotonic() - t0:.2f}s"
            + (" (SAFETY NET)" if not str(e) else "")
        )
    except BaseException as e:  # noqa
        print(f"[{name}] {type(e).__name__}({e!r}) in {time.monotonic() - t0:.2f}s")


async def main() -> None:
    print(sys.version.split()[0], zd.__file__)

    # A. xpath(timeout=0) / negative while CDP never answers
    for t in (0, -1):
        tab = new_tab()
        tab.send = never  # type: ignore
        await run(f"xpath timeout={t} blocked", tab.xpath("//x", timeout=t))

    # B. slow but working first attempt longer than timeout + 0.5
    element = object()

    async def slow_lookup(*a: Any, **k: Any) -> object:
        await asyncio.sleep(1.2)
        return element

    for meth in ("select", "find", "wait_for", "select_all", "find_all"):
        tab = new_tab()
        tab.update_target = noop  # type: ignore
        tab.query_selector = slow_lookup  # type: ignore
        tab.find_element_by_text = slow_lookup  # type: ignore

        async def slow_all(*a: Any, **k: Any) -> list[object]:
            await asyncio.sleep(1.2)
            return [element]

        tab.query_selector_all = slow_all  # type: ignore
        tab.find_elements_by_text = slow_all  # type: ignore
        await run(f"{meth} timeout=0.5 first attempt 1.2s", getattr(tab, meth)("x", timeout=0.5))

    # C. timeout=inf, element appears after 1s
    loop = asyncio.get_running_loop()
    for meth in ("select", "wait_for"):
        tab = new_tab()
        tab.update_target = noop  # type: ignore
        start = loop.time()

        async def late(*a: Any, **k: Any) -> object | None:
            return element if loop.time() - start > 1 else None

        tab.query_selector = late  # type: ignore
        await run(f"{meth} timeout=inf", getattr(tab, meth)("x", timeout=math.inf))

    # D. outer cancellation propagates as CancelledError
    tab = new_tab()
    tab.send = never  # type: ignore
    task = asyncio.ensure_future(tab.select("#x", timeout=5))
    await asyncio.sleep(0.2)
    task.cancel()
    try:
        await task
        print("[outer cancel] returned?!")
    except asyncio.CancelledError:
        print("[outer cancel] CancelledError OK")
    except BaseException as e:  # noqa
        print(f"[outer cancel] {type(e).__name__} {e!r}")

    # E. outer wait_for shorter than inner timeout -> outer TimeoutError (no message)
    tab = new_tab()
    tab.send = never  # type: ignore
    await run("outer wait_for 0.5 over select(timeout=5)", tab.select("#x", timeout=5), net=0.5)

    # F. xpath with no-op send; count attempts and time with timeout=1
    tab = new_tab()
    tab.send = noop  # type: ignore
    attempts = 0

    async def fa(*a: Any, **k: Any) -> list[object]:
        nonlocal attempts
        attempts += 1
        return []

    tab.find_all = fa  # type: ignore
    await run("xpath timeout=1 miss", tab.xpath("//x", timeout=1))
    print("   attempts:", attempts)

    # G. find_all with timeout=0 hit on internal path still works
    tab = new_tab()
    tab.send = noop  # type: ignore

    async def fet(*a: Any, **k: Any) -> list[object]:
        return [element]

    tab.find_elements_by_text = fet  # type: ignore
    await run("find_all timeout=0 hit", tab.find_all("x", timeout=0))

    # H. find_all timeout=0 miss -> asyncio.TimeoutError with message
    tab = new_tab()

    async def fet_empty(*a: Any, **k: Any) -> list[object]:
        return []

    tab.find_elements_by_text = fet_empty  # type: ignore
    await run("find_all timeout=0 miss", tab.find_all("x", timeout=0))

    # I. wait_for selector+text, selector never, text found at end
    tab = new_tab()
    tab.update_target = noop  # type: ignore

    async def none_lookup(*a: Any, **k: Any) -> None:
        return None

    async def txt(*a: Any, **k: Any) -> object:
        return element

    tab.query_selector = none_lookup  # type: ignore
    tab.find_element_by_text = txt  # type: ignore
    await run("wait_for selector miss + text hit timeout=1", tab.wait_for("#x", "t", timeout=1))


asyncio.run(main())
