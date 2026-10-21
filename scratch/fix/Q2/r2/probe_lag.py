"""Where does the time of one select/xpath attempt go on a heavy page? (loop lag)"""

import asyncio
import sys

import zendriver as zd

TICK = 0.05


async def ticker(gaps: list[tuple[float, float]], stop: asyncio.Event) -> None:
    loop = asyncio.get_running_loop()
    last = loop.time()
    while not stop.is_set():
        await asyncio.sleep(TICK)
        now = loop.time()
        if now - last > TICK + 0.05:
            gaps.append((last, now - last))
        last = now


async def main() -> None:
    print(sys.version.split()[0], zd.__file__)
    browser = await zd.start(headless=True)
    try:
        tab = browser.main_tab
        assert tab is not None
        await tab.get("about:blank")
        for n in [int(a) for a in sys.argv[1:]] or [50000, 100000]:
            await tab.evaluate(
                f"""(() => {{
                document.body.innerHTML = '';
                const f = document.createDocumentFragment();
                for (let i = 0; i < {n}; i++) {{
                    const d = document.createElement('div');
                    d.className = 'c' + (i % 7);
                    d.textContent = 'item ' + i;
                    f.appendChild(d);
                }}
                const last = document.createElement('p');
                last.id = 'last';
                last.textContent = 'needle';
                f.appendChild(last);
                document.body.appendChild(f);
                return true;
                }})()
                """
            )
            for name, coro_f in (
                ("select(#last, timeout=30)", lambda: tab.select("#last", timeout=30)),
                (
                    "xpath(//p[@id='last'], 30)",
                    lambda: tab.xpath("//p[@id='last']", timeout=30),
                ),
            ):
                gaps: list[tuple[float, float]] = []
                stop = asyncio.Event()
                loop = asyncio.get_running_loop()
                tk = asyncio.ensure_future(ticker(gaps, stop))
                t0 = loop.time()
                r = await coro_f()
                total = loop.time() - t0
                stop.set()
                await tk
                blocked = sum(g for _, g in gaps)
                print(
                    f"n={n:6d} {name:30s} {'found' if r else repr(r):6s} "
                    f"total={total:.2f}s blocked={blocked:.2f}s "
                    f"idle={total - blocked:.2f}s "
                    f"gaps={[(round(s - t0, 2), round(g, 2)) for s, g in gaps]}"
                )
    finally:
        await browser.stop()


asyncio.run(main())
