import asyncio
import pathlib
import shutil
import sys
import tempfile

import zendriver

print("zendriver from", zendriver.__file__, "python", sys.version.split()[0])

HTML = """<!doctype html><html><body>
<button id="vh" style="visibility:hidden" onclick="window.vhClicked=1">vh</button>
<button id="det" onclick="window.detClicked=1">det</button>
<script>window.keep = document.getElementById('det');</script>
</body></html>"""


async def attempt(label, fn):
    try:
        r = await asyncio.wait_for(fn(), 20)
        print(f"[{label}] OK -> {r!r}"[:200])
    except Exception as e:  # noqa
        print(f"[{label}] EXC {type(e).__module__}.{type(e).__name__}: {str(e)[:160]}")


async def main():
    tmp = pathlib.Path(tempfile.mkdtemp(prefix="r13extra-"))
    p = tmp / "p.html"
    p.write_text(HTML)
    browser = await zendriver.start(headless=True)
    try:
        tab = await browser.get(p.as_uri())
        await tab.wait_for_ready_state("complete")
        vh = await tab.select("#vh")
        await attempt("visibility:hidden click", vh.click)
        print("  vhClicked =", await tab.evaluate("window.vhClicked"))
        det = await tab.select("#det")
        await tab.evaluate("window.keep.remove(); 1")
        await attempt("detached click", det.click)
        print("  detClicked =", await tab.evaluate("window.detClicked"))
        await attempt("detached apply el.click()", lambda: det.apply("(el)=>el.click()"))
        print("  detClicked after apply =", await tab.evaluate("window.detClicked"))
    finally:
        await browser.stop()
        shutil.rmtree(tmp, ignore_errors=True)


asyncio.run(main())
