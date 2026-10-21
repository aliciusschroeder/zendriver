import asyncio
import shutil
import tempfile
import time

import zendriver as zd

print("zendriver from", zd.__file__)


async def run(label, coro):
    t = time.monotonic()
    try:
        el = await asyncio.wait_for(coro, 30)
        print(
            f"{label}: OK {time.monotonic() - t:.2f}s -> "
            f"<{el.tag} id={el.attrs.get('id')!r}> {el.text!r}"
        )
    except Exception as e:
        print(f"{label}: EXC {time.monotonic() - t:.2f}s -> {type(e).__name__}: {e}")


async def main():
    udd = tempfile.mkdtemp(prefix="q10-")
    b = await zd.start(headless=True, user_data_dir=udd)
    try:
        tab = await b.get(
            "data:text/html,<ul><li>Apples</li></ul>"
            "<p id='p1'>Hello needle world</p><button>Sign up!</button>"
        )
        await run("tab(text='Hello needle')", tab(text="Hello needle", timeout=2))
        await run("tab('Hello needle')", tab("Hello needle", timeout=2))
        await run("tab(text='Sign up!')", tab(text="Sign up!", timeout=2))
        await run("tab(selector='li')", tab(selector="li", timeout=2))
        await run("tab(text='nope-not-here')", tab(text="nope-not-here", timeout=1))
    finally:
        await b.stop()
        shutil.rmtree(udd, ignore_errors=True)


asyncio.run(main())
