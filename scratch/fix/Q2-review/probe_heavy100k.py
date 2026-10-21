"""How long does one select/find attempt take on a heavy page (real Chromium)?"""

import asyncio
import sys
import time

import zendriver as zd


async def main() -> None:
    print(sys.version.split()[0], zd.__file__)
    browser = await zd.start(headless=True)
    try:
        tab = browser.main_tab
        assert tab is not None
        await tab.get("about:blank")
        for n in (100000,):
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
                ("select(#last, timeout=2)", lambda: tab.select("#last", timeout=2)),
                ("xpath default 2.5", lambda: tab.xpath("//p[@id='last']")),
                ("select(#last, timeout=0.5)", lambda: tab.select("#last", timeout=0.5)),
                ("xpath(//p[@id='last'], 0.5)", lambda: tab.xpath("//p[@id='last']", timeout=0.5)),
            ):
                t0 = time.monotonic()
                try:
                    r = await asyncio.wait_for(coro_f(), 60)
                    res = "found" if r else repr(r)
                except asyncio.TimeoutError as e:
                    res = f"TimeoutError({e})"
                print(f"n={n:6d} {name:32s} {res:60s} {time.monotonic() - t0:.2f}s")
    finally:
        await browser.stop()


asyncio.run(main())
