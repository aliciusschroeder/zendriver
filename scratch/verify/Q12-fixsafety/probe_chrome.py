"""Real-Chromium probe for Q12 (X1: nested Runtime.enable on a busy page, X2: flash on a busy page)."""
import asyncio
import shutil
import sys
import tempfile
import time
import urllib.parse

import zendriver as zd
from zendriver import cdp

PAGE = "data:text/html," + urllib.parse.quote("""<html><body>
<button id=b onclick="window.busy=1">busy</button>
<script>
// page code that runs 4s of synchronous work when styleSheets is read after the click
const d = Object.getOwnPropertyDescriptor(Document.prototype, 'styleSheets');
Object.defineProperty(Document.prototype, 'styleSheets', {get() {
  if (window.busy) { window.busy = 0; const t = Date.now(); while (Date.now() - t < 4000) {} }
  return d.get.call(this);
}});
</script>
</body></html>""")


async def x2(tab: zd.Tab) -> None:
    btn = await tab.select("#b")
    t0 = time.monotonic()
    try:
        r = await asyncio.wait_for(btn.mouse_click(), 1.0)
        print(f"X2 mouse_click under wait_for(1.0): returned {r!r} after {time.monotonic()-t0:.2f}s (no TimeoutError)")
    except asyncio.TimeoutError:
        print(f"X2 mouse_click under wait_for(1.0): TimeoutError after {time.monotonic()-t0:.2f}s")
    await asyncio.sleep(4.5)  # let the busy loop end


async def x1(tab: zd.Tab) -> None:
    # make the renderer main thread busy forever, then register a Runtime handler
    await tab.evaluate("setTimeout(()=>{while(true){}}, 50)")
    await asyncio.sleep(0.5)
    tab.add_handler(cdp.runtime.ConsoleAPICalled, lambda e: None)
    t0 = time.monotonic()
    task = asyncio.ensure_future(
        asyncio.wait_for(tab.send(cdp.target.get_target_info()), 2.0)
    )
    done, _ = await asyncio.wait({task}, timeout=8)
    if task in done:
        exc = task.exception()
        print(f"X1 send under wait_for(2.0): finished after {time.monotonic()-t0:.2f}s with {exc!r}" if exc else f"X1 send under wait_for(2.0): result after {time.monotonic()-t0:.2f}s")
    else:
        print(f"X1 send under wait_for(2.0): STILL RUNNING after {time.monotonic()-t0:.2f}s; enabled_domains={[m.__name__ for m in tab.enabled_domains]}")
        task.print_stack()
        task.cancel()
        await asyncio.wait({task}, timeout=2)
        print("X1 after a 2nd cancel: done=", task.done())


async def main() -> None:
    print("zendriver from", zd.__file__, "python", sys.version.split()[0])
    tmp = tempfile.mkdtemp(prefix="q12fs-", dir=sys.argv[1])
    browser = await zd.start(headless=True, user_data_dir=tmp)
    try:
        tab = await browser.get(PAGE)
        await x2(tab)
        await x1(tab)
    finally:
        await browser.stop()
        shutil.rmtree(tmp, ignore_errors=True)


asyncio.run(main())
