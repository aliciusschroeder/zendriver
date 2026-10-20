import asyncio, urllib.parse, warnings, http.server, threading, os, tempfile
warnings.simplefilter("ignore")
import zendriver
print("zendriver from", zendriver.__file__)

HTML = """<html><body>
<div id=wrap><my-list items='[1,2]'></my-list></div>
<br id=b clear=all>
<span id=s get=g>hello</span>
<a id=lnk href="http://example.com/x" items="3">link</a>
<p id=ctrl data-x=1>control</p>
</body></html>"""

async def step(label, coro_fn):
    try:
        r = coro_fn()
        if asyncio.iscoroutine(r) or isinstance(r, asyncio.Future) or hasattr(r, "__await__"):
            r = await asyncio.wait_for(r, 20)
        s = repr(r)
        print(f"OK   {label} -> {s[:120]}")
    except Exception as e:
        print(f"FAIL {label} -> {type(e).__name__}: {e}")

async def main():
    # serve over http so get_all_urls has a proper url
    tmp = tempfile.mkdtemp(dir=os.path.dirname(__file__))
    with open(os.path.join(tmp, "index.html"), "w") as f:
        f.write(HTML)
    handler = lambda *a, **k: http.server.SimpleHTTPRequestHandler(*a, directory=tmp, **k)
    srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    url = f"http://127.0.0.1:{srv.server_address[1]}/index.html"
    browser = await zendriver.start(headless=True)
    try:
        tab = await browser.get(url)
        await tab.wait_for("#ctrl", timeout=10)
        br = await tab.select("#b")
        print("br.attrs =", dict(br.attrs))
        await step("await br", lambda: br)
        await step("br.update()", lambda: br.update())
        await step("br.query_selector('x')", lambda: br.query_selector("x"))
        await step("repr(br)", lambda: repr(br))
        ctrl = await tab.select("#ctrl")
        await step("control: ctrl.update()", lambda: ctrl.update())
        await step("control: repr(ctrl)", lambda: repr(ctrl))
        wrap = await tab.select("#wrap")
        await step("str(wrap) (child my-list has items=)", lambda: str(wrap))
        ml = await tab.select("my-list")
        await step("repr(my-list)", lambda: repr(ml))
        s = await tab.select("#s")
        print("s.attrs =", dict(s.attrs))
        await step("s.get('id')", lambda: s.get("id"))
        await step("s['id']", lambda: s["id"])
        await step("s.id (__getattr__)", lambda: s.id)
        await step("control: ctrl.get('id')", lambda: ctrl.get("id"))
        await step("tab.get_all_urls()", lambda: tab.get_all_urls())
        await step("tab.get_all_urls(absolute=False)", lambda: tab.get_all_urls(absolute=False))
        async def js():
            j = await br.__class__.get_js_attributes(br) if False else None
        # get_js_attributes on a fresh br element (update fails, so use a newly selected one)
        br2 = await tab.select("#b")
        async def jsclear():
            ja = await br2.get_js_attributes()
            print("   js attrs has 'clear' key:", 'clear' in ja, repr(ja.get('clear') if False else dict.get(ja, 'clear')))
            return ja.clear()
        await step("br.get_js_attributes().clear()", jsclear)
        br3 = await tab.select("#b")
        await step("br.save_to_dom()", lambda: br3.save_to_dom())
        br4 = await tab.select("#b")
        await step("br.remove_from_dom()", lambda: br4.remove_from_dom())
        print("br still in DOM after remove_from_dom:", (await tab.select("#b", timeout=1)) is not None if True else None)
    finally:
        await browser.stop()
        srv.shutdown()
        import shutil; shutil.rmtree(tmp, ignore_errors=True)

asyncio.run(main())
