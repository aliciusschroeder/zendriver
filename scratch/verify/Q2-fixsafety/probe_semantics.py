"""Behaviour-change probe on real Chromium: small timeouts, timeout=0, recovery after a dialog."""

import asyncio
import logging
import time

import zendriver
from zendriver import cdp

print("zendriver from", zendriver.__file__)

errors: list[str] = []


class Catch(logging.Handler):
    def emit(self, record: logging.LogRecord) -> None:
        if record.levelno >= logging.ERROR:
            errors.append(record.getMessage()[:200])


logging.getLogger().addHandler(Catch())


async def timed(name, coro, outer=10):
    t0 = time.monotonic()
    try:
        r = await asyncio.wait_for(coro, outer)
        out = f"returned {type(r).__name__}{'(len=%d)' % len(r) if isinstance(r, list) else ''}"
    except BaseException as e:  # noqa
        out = f"{type(e).__name__}({str(e)[:70]})"
    print(f"{name}: {out} after {time.monotonic() - t0:.3f}s")


async def main():
    loop = asyncio.get_running_loop()
    loop.set_exception_handler(lambda l, ctx: errors.append(str(ctx.get("message"))[:200]))
    browser = await zendriver.start(headless=True)
    try:
        tab = browser.main_tab
        await tab.get("data:text/html,<p id=topp>hi</p>")
        await tab.select("#topp", timeout=5)
        # ---- timeout <= 0 and tiny timeouts with the element present
        await timed("select('#topp', timeout=0)", tab.select("#topp", timeout=0))
        await timed("find('hi', timeout=0)", tab.find("hi", timeout=0))
        await timed("wait_for(selector='#topp', timeout=0)", tab.wait_for(selector="#topp", timeout=0))
        await timed("xpath('//p[@id=\"topp\"]', timeout=0)", tab.xpath('//p[@id="topp"]', timeout=0))
        await timed("xpath('//p[@id=\"topp\"]') default", tab.xpath('//p[@id="topp"]'))
        await timed("select('#topp', timeout=0.001)", tab.select("#topp", timeout=0.001))
        await timed("select('#topp', timeout=0.05)", tab.select("#topp", timeout=0.05))
        await timed("find('hi', timeout=0.05)", tab.find("hi", timeout=0.05))
        # ---- element that appears 300 ms later, timeout=0.5
        await tab.evaluate(
            "setTimeout(()=>{const d=document.createElement('div');d.id='late';d.textContent='late';document.body.appendChild(d)},300)",
            await_promise=False,
        )
        await timed("select('#late', timeout=0.5) [appears at 0.3s]", tab.select("#late", timeout=0.5))
        await tab.evaluate("document.getElementById('late')?.remove()")
        await tab.evaluate(
            "setTimeout(()=>{const d=document.createElement('div');d.id='late2';document.body.appendChild(d)},700)",
            await_promise=False,
        )
        await timed("select('#late2', timeout=1) [appears at 0.7s]", tab.select("#late2", timeout=1))
        # ---- xpath send count on a miss
        count = 0
        orig_send = tab.send

        async def counting_send(*a, **k):
            nonlocal count
            count += 1
            return await orig_send(*a, **k)

        tab.send = counting_send  # instance attribute
        await timed("xpath('//nope', timeout=0.5)", tab.xpath("//nope", timeout=0.5))
        print("   CDP sends during that xpath call:", count)
        del tab.send
        # ---- recovery after a dialog
        await tab.send(cdp.page.enable())  # needed for Page.handleJavaScriptDialog
        await tab.evaluate("setTimeout(()=>alert('x'),100)", await_promise=False)
        await asyncio.sleep(0.6)
        await timed("blocked select('#topp', timeout=1)", tab.select("#topp", timeout=1), outer=5)
        await timed("blocked xpath('//p', timeout=1)", tab.xpath("//p", timeout=1), outer=5)
        try:
            await tab.send(cdp.page.handle_java_script_dialog(accept=True))
        except Exception as e:
            print("   handleJavaScriptDialog:", str(e).splitlines()[0])
        await asyncio.sleep(0.5)
        await timed("after dismiss select('#topp', timeout=2)", tab.select("#topp", timeout=2))
        await timed("after dismiss find('hi', timeout=2)", tab.find("hi", timeout=2))
        await timed("after dismiss xpath('//p', timeout=2)", tab.xpath("//p", timeout=2))
        print("   pending transactions left in mapper:", len(tab.mapper), [t.method for t in tab.mapper.values()])
    finally:
        await browser.stop()
    print("loop/logging errors:", errors)


asyncio.run(main())
