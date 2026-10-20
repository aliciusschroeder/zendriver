import asyncio, time, sys, tempfile, shutil, os
import zendriver
from zendriver.core.connection import ProtocolException
print("zendriver from", zendriver.__file__, "python", sys.version.split()[0])

HTML = """<html><head><title>happy page</title>
<script>var x = 'please press';</script></head>
<body><div class="wrap" id="d1">spam</div>
<p id="p1">Hello needle world</p>
<button id="b1">Sign up!</button>
<ul><li>Apples</li><li>Pears</li></ul>
</body></html>"""

async def attempt(label, coro):
    t = time.monotonic()
    try:
        r = await asyncio.wait_for(coro, 30)
        print(f"[{label}] OK {time.monotonic()-t:.2f}s -> {r!r}"[:300])
    except asyncio.TimeoutError as e:
        print(f"[{label}] TimeoutError {time.monotonic()-t:.2f}s: {e}")
    except ProtocolException as e:
        print(f"[{label}] ProtocolException {time.monotonic()-t:.2f}s: {e}")
    except Exception as e:
        print(f"[{label}] {type(e).__name__} {time.monotonic()-t:.2f}s: {e}")

async def main():
    tmp = tempfile.mkdtemp(dir=os.path.dirname(os.path.abspath(__file__)))
    path = os.path.join(tmp, "page.html")
    open(path, "w").write(HTML)
    browser = await zendriver.start(headless=True)
    try:
        tab = await browser.get("file://" + path)
        await tab.wait_for_ready_state("complete")
        await attempt("tab(text='Hello needle', timeout=2)", tab(text="Hello needle", timeout=2))
        await attempt("tab('Hello needle', timeout=2) positional", tab("Hello needle", timeout=2))
        await attempt("wait_for(text='Hello needle', timeout=2)", tab.wait_for(text="Hello needle", timeout=2))
        await attempt("tab(text='Apples', timeout=2)", tab(text="Apples", timeout=2))
        await attempt("wait_for(text='Apples', timeout=2)", tab.wait_for(text="Apples", timeout=2))
        await attempt("tab(text='Sign up!', timeout=2)", tab(text="Sign up!", timeout=2))
        await attempt("wait_for(text='Sign up!', timeout=2)", tab.wait_for(text="Sign up!", timeout=2))
        await attempt("tab(selector='#p1', timeout=2)", tab(selector="#p1", timeout=2))
        await attempt("wait_for(selector='#p1', timeout=2)", tab.wait_for(selector="#p1", timeout=2))
        await attempt("tab(selector='p', timeout=2)", tab(selector="p", timeout=2))
        await attempt("wait_for(selector='p', timeout=2)", tab.wait_for(selector="p", timeout=2))
        await attempt("tab(selector='li', timeout=2)", tab(selector="li", timeout=2))
        await attempt("tab(selector='ul > li:nth-child(2)', timeout=2)", tab(selector="ul > li:nth-child(2)", timeout=2))
        await attempt("wait_for(selector='ul > li:nth-child(2)', timeout=2)", tab.wait_for(selector="ul > li:nth-child(2)", timeout=2))
        await attempt("tab(selector='.wrap', timeout=2)", tab(selector=".wrap", timeout=2))
        # both given: text wins first because it goes to selector slot
        await attempt("tab(text='Hello needle', selector='#b1', timeout=2)", tab(text="Hello needle", selector="#b1", timeout=2))
        await attempt("wait_for(text='Hello needle', selector='#b1', timeout=2)", tab.wait_for(text="Hello needle", selector="#b1", timeout=2))
    finally:
        await browser.stop()
        shutil.rmtree(tmp, ignore_errors=True)

asyncio.run(main())
