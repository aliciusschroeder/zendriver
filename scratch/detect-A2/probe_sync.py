import asyncio, gc, threading, warnings, http.server, functools
import zendriver as zd
from zendriver import cdp

warnings.simplefilter("always")
seen = []
errors = []

async def main():
    loop = asyncio.get_running_loop()
    def exc_handler(loop, ctx):
        errors.append(repr(ctx.get("exception")) + " | " + ctx.get("message", ""))
    loop.set_exception_handler(exc_handler)
    srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), http.server.SimpleHTTPRequestHandler)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    base = f"http://127.0.0.1:{srv.server_address[1]}/"
    browser = await zd.start(headless=True)
    try:
        tab = await browser.get(base)
        # sync handler, as the feed_cdp docstring suggests ("not an async method")
        def on_paused(ev: cdp.fetch.RequestPaused):
            seen.append(threading.current_thread().name)
            tab.feed_cdp(cdp.fetch.continue_request(request_id=ev.request_id))
        tab.add_handler(cdp.fetch.RequestPaused, on_paused)
        await tab.send(cdp.fetch.enable())
        try:
            r = await asyncio.wait_for(tab.send(cdp.runtime.evaluate(
                "fetch('/probe_sync.py').then(r=>r.status)", await_promise=True)), 5)
            print("fetch completed:", r[0].value, "handler threads:", seen)
        except asyncio.TimeoutError:
            print("page fetch HUNG: request stayed paused (handler ran in thread", seen, ")")
        # lambda returning a coroutine
        got = []
        async def process(e): got.append(e)
        tab.add_handler(cdp.runtime.ConsoleAPICalled, lambda e: process(e))
        await tab.send(cdp.fetch.disable())
        await tab.send(cdp.runtime.evaluate("console.log('x')"))
        await asyncio.sleep(1)
        print("async work scheduled by lambda ran:", len(got))
        gc.collect()
        await asyncio.sleep(0.2)
    finally:
        await browser.stop()
    print("loop errors:", errors)

asyncio.run(asyncio.wait_for(main(), 50))
