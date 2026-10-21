"""Real Chromium: more methods on a tab blocked by alert(); heavy-page timing."""

import asyncio
import sys
import time
from typing import Any, Awaitable, Callable

import zendriver as zd


async def timed(name: str, make: Callable[[], Awaitable[Any]], net: float = 8) -> None:
    t0 = time.monotonic()
    task = asyncio.ensure_future(make())
    done, _ = await asyncio.wait({task}, timeout=net)
    dt = time.monotonic() - t0
    if not done:
        task.cancel()
        try:
            await asyncio.wait_for(task, 2)
        except BaseException:  # noqa
            pass
        print(f"[{name}] STILL PENDING after {dt:.2f}s")
        return
    exc = task.exception()
    if exc is not None:
        print(f"[{name}] {type(exc).__name__}({exc}) in {dt:.2f}s")
    else:
        r = task.result()
        desc = f"list[{len(r)}]" if isinstance(r, list) else ("element" if r else r)
        print(f"[{name}] -> {desc} in {dt:.2f}s")


async def main() -> None:
    print(sys.version.split()[0], zd.__file__)
    browser = await zd.start(headless=True)
    try:
        tab = browser.main_tab
        assert tab is not None
        await tab.get(
            "data:text/html,<p id=topp>hello</p><iframe srcdoc='<b id=inner>x</b>'></iframe>"
        )
        await asyncio.sleep(0.5)
        await timed("select include_frames (ok page)", lambda: tab.select("#inner", timeout=2, include_frames=True))
        await tab.evaluate("setTimeout(() => alert('blocking'), 200)", await_promise=False)
        await asyncio.sleep(1)
        await timed("find_all t=1", lambda: tab.find_all("hello", timeout=1))
        await timed("select_all t=1", lambda: tab.select_all("p", timeout=1))
        await timed("select include_frames t=1", lambda: tab.select("#inner", timeout=1, include_frames=True))
        await timed("find include_frames t=1", lambda: tab.find("x", timeout=1, include_frames=True))
        await timed("select_all include_frames t=1", lambda: tab.select_all("b", timeout=1, include_frames=True))
        await timed("xpath t=-1", lambda: tab.xpath("//p", timeout=-1))
        await tab.get("data:text/html,<p id=ok>ok</p>")

        # heavy page: one attempt timing, fix vs base
        n = 50000
        await tab.get("data:text/html,<div id=root></div>")
        await tab.evaluate(
            f"(() => {{ const r = document.getElementById('root'); for (let i=0;i<{n};i++) {{ const d=document.createElement('span'); d.textContent='s'+i; r.appendChild(d);}} const l=document.createElement('p'); l.id='last'; r.appendChild(l); }})()"
        )
        await timed(f"heavy {n} select(#last, t=1)", lambda: tab.select("#last", timeout=1), net=20)
        await timed(f"heavy {n} select(#last, t=10)", lambda: tab.select("#last", timeout=10), net=20)
        await timed(f"heavy {n} xpath(//p[@id='last'], default)", lambda: tab.xpath("//p[@id='last']"), net=20)
    finally:
        await browser.stop()


asyncio.run(main())
