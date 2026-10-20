import asyncio, sys, urllib.parse, warnings
import zendriver
print("zendriver from", zendriver.__file__, "py", sys.version.split()[0])
warnings.simplefilter("ignore")
HTML = "<body><div id=wrap><my-list items='[1,2]'></my-list></div><br id=b clear=all><span id=s get=g>t</span><a items=3 href='http://x.example/a'>l</a></body>"

async def step(label, coro):
    try:
        r = await asyncio.wait_for(coro, 20)
        print(f"{label}: OK -> {str(r)[:80]!r}")
    except Exception as e:
        print(f"{label}: {type(e).__name__}: {e}")

async def main():
    browser = await zendriver.start(headless=True)
    try:
        tab = await browser.get("data:text/html," + urllib.parse.quote(HTML))
        br = await tab.select("#b")
        print("br attrs", dict(br.attrs))
        await step("await br.update()", br.update())
        await step("await br.query_selector('x')", br.query_selector("x"))
        wrap = await tab.select("#wrap")
        async def s(): return str(wrap)
        await step("str(#wrap)", s())
        sp = await tab.select("#s")
        async def g(): return sp.get("id")
        await step("span.get('id')", g())
        await step("tab.get_all_urls()", tab.get_all_urls())
        async def js():
            j = await br.get_js_attributes()
            return j.clear()
        await step("br.get_js_attributes().clear()", js())
    finally:
        await browser.stop()

asyncio.run(asyncio.wait_for(main(), 90))
