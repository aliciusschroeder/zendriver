import asyncio
import time
from typing import Any

import zendriver as zd


async def noop(*a: Any, **k: Any) -> None:
    return None


async def never(*a: Any, **k: Any) -> None:
    await asyncio.Event().wait()


async def main() -> None:
    print(zd.__file__)
    obj = object()
    tab = zd.Tab.__new__(zd.Tab)
    tab.send = noop  # type: ignore
    n = 0

    async def fa(*a: Any, **k: Any) -> list[object]:
        nonlocal n
        n += 1
        return [obj]

    tab.find_all = fa  # type: ignore
    print("timeout=0 hit:", await tab.xpath("//x", timeout=0) == [obj], "attempts", n)
    tab2 = zd.Tab.__new__(zd.Tab)
    tab2.send = never  # type: ignore
    for t in (0, 1):
        t0 = time.monotonic()
        try:
            r = await asyncio.wait_for(tab2.xpath("//x", timeout=t), 5)
            print(f"timeout={t} blocked:", r, f"{time.monotonic() - t0:.2f}s")
        except asyncio.TimeoutError:
            print(f"timeout={t} blocked: SAFETY NET", f"{time.monotonic() - t0:.2f}s")


asyncio.run(main())
