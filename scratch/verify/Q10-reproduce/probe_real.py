"""Real headless Chromium: tab(text=...) vs tab.wait_for(text=...)."""
import asyncio
import os
import pathlib
import time
import urllib.parse

import zendriver
from zendriver.core.connection import ProtocolException

print("zendriver from:", zendriver.__file__)

HTML = (
    "<html><body>"
    "<p id='p1'>Hello needle world</p>"
    "<button id='b'>Sign up!</button>"
    "<ul><li>Apples</li><li>Pears</li></ul>"
    "</body></html>"
)


async def attempt(label, coro_factory):
    t0 = time.monotonic()
    try:
        r = await asyncio.wait_for(coro_factory(), 30)
        desc = None if r is None else f"<{r.tag_name} id={r.attrs.get('id')!r}> text={r.text!r}"
        print(f"[{label}] OK in {time.monotonic()-t0:.2f}s -> {desc}")
    except Exception as e:  # noqa: BLE001
        print(f"[{label}] EXC in {time.monotonic()-t0:.2f}s -> {type(e).__name__}: {e!s:.150}")


async def main() -> None:
    d = pathlib.Path(os.environ["SCR"]) / "page.html"
    d.write_text(HTML)
    browser = await zendriver.start(headless=True)
    try:
        tab = await browser.get(d.as_uri())
        await tab.wait_for_ready_state("complete")
        await attempt("wait_for(text='Hello needle', timeout=2)", lambda: tab.wait_for(text="Hello needle", timeout=2))
        await attempt("tab(text='Hello needle', timeout=2)", lambda: tab(text="Hello needle", timeout=2))
        await attempt("tab('Hello needle', timeout=2)  [positional]", lambda: tab("Hello needle", timeout=2))
        await attempt("wait_for(text='Sign up!', timeout=2)", lambda: tab.wait_for(text="Sign up!", timeout=2))
        await attempt("tab(text='Sign up!', timeout=2)", lambda: tab(text="Sign up!", timeout=2))
        await attempt("wait_for(text='Apples', timeout=2)", lambda: tab.wait_for(text="Apples", timeout=2))
        await attempt("tab(text='Apples', timeout=2)", lambda: tab(text="Apples", timeout=2))
        # selector path
        await attempt("wait_for(selector='#p1', timeout=2)", lambda: tab.wait_for(selector="#p1", timeout=2))
        await attempt("tab(selector='#p1', timeout=2)", lambda: tab(selector="#p1", timeout=2))
        await attempt("wait_for(selector='li', timeout=2)", lambda: tab.wait_for(selector="li", timeout=2))
        await attempt("tab(selector='li', timeout=2)", lambda: tab(selector="li", timeout=2))
        # selector that does not exist yet -> show it is routed into find_element_by_text
        calls = []
        orig_q = tab.query_selector
        orig_t = tab.find_element_by_text

        async def q(sel, *a, **k):
            calls.append(("query_selector", sel))
            return await orig_q(sel, *a, **k)

        async def t(txt, *a, **k):
            calls.append(("find_element_by_text", txt))
            return await orig_t(txt, *a, **k)

        tab.query_selector = q
        tab.find_element_by_text = t
        await attempt("tab(text='Hello needle', timeout=1) [traced]", lambda: tab(text="Hello needle", timeout=1))
        print("   calls:", sorted(set(calls)))
        calls.clear()
        await attempt("tab(selector='#p1', timeout=1) [traced]", lambda: tab(selector="#p1", timeout=1))
        print("   calls:", sorted(set(calls)))
        calls.clear()
        await attempt("wait_for(text='Hello needle', timeout=1) [traced]", lambda: tab.wait_for(text="Hello needle", timeout=1))
        print("   calls:", sorted(set(calls)))
        tab.query_selector = orig_q
        tab.find_element_by_text = orig_t
    finally:
        await browser.stop()


asyncio.run(main())
