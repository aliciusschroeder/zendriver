import asyncio, sys, pathlib, time
import zendriver as zd
from zendriver import cdp
print("zendriver from", zd.__file__, sys.version.split()[0])
HERE = pathlib.Path(__file__).parent

def show(task):
    if not task.done(): return "pending"
    if task.cancelled(): return "cancelled"
    e = task.exception()
    if e: return f"EXC {type(e).__name__}: {str(e)[:200]}"
    r = task.result()
    return f"result len={len(r) if r else r!r} head={r[:30] if r else r!r}"

async def main():
    browser = await zd.start(headless=True)
    try:
        tab = await browser.get((HERE / "page.html").as_uri())
        await tab.sleep(0.5)
        mir = await tab.select("#mir")
        t0 = time.monotonic()
        task = asyncio.ensure_future(mir.screenshot_b64(format="png"))
        await asyncio.wait([task], timeout=40)
        print(f"[static idle] after {time.monotonic()-t0:.0f}s:", show(task))
        if not task.done():
            task.print_stack(limit=2, file=sys.stdout)
            await tab.evaluate("document.getElementById('plain').style.background='#ff0'")
            await asyncio.wait([task], timeout=10)
            print(f"[static after DOM repaint] after {time.monotonic()-t0:.0f}s:", show(task))
        if not task.done():
            r = await asyncio.wait_for(tab.screenshot_b64(format="png"), 15)
            await asyncio.wait([task], timeout=10)
            print(f"[static after tab.screenshot] after {time.monotonic()-t0:.0f}s:", show(task))
        if not task.done():
            task.cancel()
        # animated page
        tab = await tab.get((HERE / "anim.html").as_uri())
        await tab.sleep(0.5)
        mir = await tab.select("#mir")
        t0 = time.monotonic()
        task = asyncio.ensure_future(mir.screenshot_b64(format="png"))
        await asyncio.wait([task], timeout=40)
        print(f"[animated page] after {time.monotonic()-t0:.1f}s:", show(task))
        if not task.done(): task.cancel()
        # rotate(180) on animated page via raw
        t0 = time.monotonic()
        task = asyncio.ensure_future(tab.send(cdp.page.capture_screenshot("png", clip=cdp.page.Viewport(x=250,y=90,width=-100,height=-40,scale=1), capture_beyond_viewport=True)))
        await asyncio.wait([task], timeout=40)
        print(f"[animated page raw neg w/h] after {time.monotonic()-t0:.1f}s:", show(task))
        if not task.done(): task.cancel()
    finally:
        await browser.stop()

asyncio.run(main())
