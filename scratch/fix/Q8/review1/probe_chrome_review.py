import asyncio
import warnings

import zendriver as zd

HTML = (
    "data:text/html,<body><div id=wrap><my-list items='[1,2]'></my-list></div>"
    "<center id=c><br id=b clear=all><a href='http://y.example/b'>y</a></center>"
    "<span id=s get=g values=v></span>"
    "<a items=3 href='http://x.example/a'>x</a></body>"
)


async def step(label, coro_or_fn):
    try:
        r = coro_or_fn()
        if asyncio.iscoroutine(r):
            r = await r
        print(f"OK   {label}: {r!r}"[:220])
    except Exception as e:
        print(f"FAIL {label}: {type(e).__name__}: {e}"[:220])


async def main() -> None:
    warnings.simplefilter("ignore")
    print("zendriver from", zd.__file__)
    browser = await zd.start(headless=True)
    try:
        tab = await browser.get(HTML)
        br = await tab.select("#b")
        await step("await br", lambda: br.__await__ and _await(br))
        await step("br.update()", lambda: br.update())
        await step("br.query_selector_all('x')", lambda: br.query_selector_all("x"))
        await step("br.clear via Element.__getattr__", lambda: br.clear)
        await step("br['clear']", lambda: br["clear"])
        center = await tab.select("#c")
        await step(
            "iterate center.children query_selector_all('a')",
            lambda: _iter_children(center),
        )
        wrap = await tab.select("#wrap")
        await step("str(wrap)", lambda: str(wrap))
        s = await tab.select("#s")
        await step("s.get('id')", lambda: s.get("id"))
        await step("s['get']", lambda: s["get"])
        await step("s.id (deprecated)", lambda: s.id)
        await step("s.attrs.values()", lambda: list(s.attrs.values()))
        await step("tab.get_all_urls()", lambda: tab.get_all_urls())
        js = await br.get_js_attributes()
        await step("js['clear']", lambda: js["clear"])
        await step("js.clear()", lambda: (js.clear(), len(js))[1])
        await step("br.save_to_dom()", lambda: br.save_to_dom())
        await step("br.remove_from_dom()", lambda: br.remove_from_dom())
        await step("br gone", lambda: tab.select_all("#b", timeout=1))
    finally:
        await browser.stop()


async def _await(el):
    return await el


async def _iter_children(center):
    out = []
    for ch in center.children:
        out.append(len(await ch.query_selector_all("a")))
    return out


asyncio.run(main())
