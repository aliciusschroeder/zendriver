import asyncio, pathlib, time
import zendriver as zd
from zendriver import cdp
PAGE = pathlib.Path(__file__).parent / "page1.html"
async def main():
    browser = await zd.start(headless=True)
    try:
        tab = await browser.get(PAGE.as_uri())
        await tab.sleep(0.5)
        inp = await tab.query_selector("#inp")
        await inp.apply("(e) => 1")
        first = inp._remote_object.object_id
        ids = set()
        N = 3000
        t = time.monotonic()
        for _ in range(N):
            await inp.apply("(e) => 1")
            ids.add(inp._remote_object.object_id)
        print(f"{N} apply() calls in {time.monotonic()-t:.1f}s -> {len(ids)} distinct object ids")
        r, exc = await tab.send(cdp.runtime.call_function_on("function(){return this.id}", object_id=first, return_by_value=True))
        print("first object id still alive after", N, "calls:", r.value, exc)
    finally:
        await asyncio.wait_for(browser.stop(), 20)
asyncio.run(main())
