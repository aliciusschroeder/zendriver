import asyncio, sys, tempfile, shutil, os
import zendriver
print("zendriver from", zendriver.__file__, "python", sys.version.split()[0])
HTML = """<html><head><title>a happy page</title></head>
<body><div id="first">alpha beta gamma</div><span>linkedin</span>
<a id="link" href="#">click</a>
<ul><li>Apples</li></ul>
<div id="x" data-q="button">bar</div><button id="btn">ok</button>
</body></html>"""
async def main():
    tmp = tempfile.mkdtemp(dir=os.path.dirname(os.path.abspath(__file__)))
    path = os.path.join(tmp, "page.html"); open(path, "w").write(HTML)
    browser = await zendriver.start(headless=True)
    try:
        tab = await browser.get("file://" + path)
        await tab.wait_for_ready_state("complete")
        for sel in ["a", "li", "button", "div", "title", "#nonexistent"]:
            for label, coro in [("tab(selector)", tab(selector=sel, timeout=1)), ("wait_for(selector)", tab.wait_for(selector=sel, timeout=1))]:
                try:
                    r = await asyncio.wait_for(coro, 20)
                    print(f"{sel!r:16} {label:20} -> {r!r}"[:200])
                except Exception as e:
                    print(f"{sel!r:16} {label:20} -> {type(e).__name__}: {e}"[:200])
    finally:
        await browser.stop(); shutil.rmtree(tmp, ignore_errors=True)
asyncio.run(main())
