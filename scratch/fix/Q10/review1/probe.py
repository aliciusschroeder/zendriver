import asyncio
import time
import urllib.parse

import zendriver as zd

HTML = (
    "<ul><li>Apples</li><li>Pears</li></ul>"
    "<p id='p1'>Hello needle world</p>"
    "<button class='go'>Sign up!</button><span>linkedin</span>"
)


async def run(label, coro):
    t = time.monotonic()
    try:
        r = await coro
        print(f"[{label}] OK {time.monotonic() - t:.2f}s -> <{r.tag_name}> {r.text!r}")
    except Exception as e:
        print(
            f"[{label}] EXC {time.monotonic() - t:.2f}s -> "
            f"{type(e).__name__}: {str(e)[:90]}"
        )


async def main():
    print("zendriver from", zd.__file__)
    browser = await zd.start(headless=True)
    try:
        tab = await browser.get("data:text/html," + urllib.parse.quote(HTML))
        await run("tab(text='Hello needle')", tab(text="Hello needle", timeout=2))
        await run("tab('Hello needle')", tab("Hello needle", timeout=2))
        await run("tab(text='Sign up!')", tab(text="Sign up!", timeout=2))
        await run("tab(selector='li')", tab(selector="li", timeout=2))
        await run("tab(selector='button.go')", tab(selector="button.go", timeout=2))
        await run("tab(selector='table') missing", tab(selector="table", timeout=1))
        await run(
            "tab(selector='Sign up!') invalid css", tab(selector="Sign up!", timeout=1)
        )
        await run(
            "tab(text='nope-not-here', timeout=1)", tab(text="nope-not-here", timeout=1)
        )
        await run(
            "tab(text='Hello needle', selector='button.go')",
            tab(text="Hello needle", selector="button.go", timeout=2),
        )
        await run(
            "tab(text='Hello needle', selector='h1')",
            tab(text="Hello needle", selector="h1", timeout=1),
        )
        await run("tab() neither", tab(timeout=1))
    finally:
        await browser.stop()


asyncio.run(main())
