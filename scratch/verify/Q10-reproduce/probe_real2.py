"""Real headless Chromium: tab(selector=...) is a text search, so it can return the wrong element;
plus the repo's groceries.html sample with tab(text='Apples')."""
import asyncio
import os
import pathlib
import time

import zendriver

print("zendriver from:", zendriver.__file__)

HTML = "<html><body><p id='hint'>press the button below</p><button id='go'>Go</button></body></html>"


async def attempt(label, coro_factory):
    t0 = time.monotonic()
    try:
        r = await asyncio.wait_for(coro_factory(), 30)
        desc = None if r is None else f"<{r.tag_name} id={r.attrs.get('id')!r}> text={r.text!r}"
        print(f"[{label}] OK in {time.monotonic()-t0:.2f}s -> {desc}")
    except Exception as e:  # noqa: BLE001
        print(f"[{label}] EXC in {time.monotonic()-t0:.2f}s -> {type(e).__name__}: {e!s:.120}")


async def main() -> None:
    d = pathlib.Path(os.environ["SCR"]) / "page2.html"
    d.write_text(HTML)
    browser = await zendriver.start(headless=True)
    try:
        tab = await browser.get(d.as_uri())
        await tab.wait_for_ready_state("complete")
        await attempt("wait_for(selector='button')", lambda: tab.wait_for(selector="button", timeout=2))
        await attempt("tab(selector='button')", lambda: tab(selector="button", timeout=2))
        g = pathlib.Path("/home/user/zendriver/tests/sample_data/groceries.html")
        tab = await browser.get(g.as_uri())
        await tab.wait_for_ready_state("complete")
        await attempt("groceries wait_for(text='Apples')", lambda: tab.wait_for(text="Apples", timeout=1))
        await attempt("groceries tab(text='Apples')", lambda: tab(text="Apples", timeout=1))
    finally:
        await browser.stop()


asyncio.run(main())
