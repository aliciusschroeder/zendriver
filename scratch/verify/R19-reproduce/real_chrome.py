"""Real headless Chromium reproducer for R19 (sync RequestPaused handler + feed_cdp)."""
import asyncio, sys, threading, http.server, functools, io
import zendriver
from zendriver import cdp

print("zendriver from", zendriver.__file__, "python", sys.version.split()[0])

class H(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        body = b"<html><head><title>OK</title></head><body>hi</body></html>"
        self.send_response(200); self.send_header("Content-Type", "text/html"); self.send_header("Content-Length", str(len(body))); self.end_headers(); self.wfile.write(body)
    def log_message(self, *a): pass

def serve():
    srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), H)
    t = threading.Thread(target=srv.serve_forever, daemon=True); t.start()
    return srv

async def run(kind, browser, url):
    tab = await browser.get("about:blank", new_tab=True)
    calls = []
    paused_ids = []
    errors = []
    tab.add_handler(cdp.fetch.RequestPaused, lambda ev: paused_ids.append(ev.request_id))
    loop = asyncio.get_running_loop()
    loop.set_exception_handler(lambda l, ctx: errors.append(repr(ctx.get("exception")) + " | " + ctx.get("message", "")))
    if kind == "async":
        async def on_paused(ev):
            calls.append((threading.current_thread().name, ev.request.url))
            tab.feed_cdp(cdp.fetch.continue_request(request_id=ev.request_id))
    elif kind == "sync":
        def on_paused(ev):
            calls.append((threading.current_thread().name, ev.request.url))
            tab.feed_cdp(cdp.fetch.continue_request(request_id=ev.request_id))
    elif kind == "lambda-conn":
        on_paused = lambda ev, t: (calls.append((threading.current_thread().name, ev.request.url)), t.feed_cdp(cdp.fetch.continue_request(request_id=ev.request_id)))
    tab.add_handler(cdp.fetch.RequestPaused, on_paused)
    await tab.send(cdp.fetch.enable())
    nav = asyncio.create_task(tab.send(cdp.page.navigate(url)))
    done, _ = await asyncio.wait({nav}, timeout=8)
    if nav in done:
        title = await asyncio.wait_for(tab.evaluate("document.title"), 5)
        print(f"  kind={kind}: navigate returned {nav.result()[0]!r}; title={title!r}; handler calls={calls}")
    else:
        print(f"  kind={kind}: page.navigate HUNG > 8s; handler calls={calls}")
        buf = io.StringIO(); nav.print_stack(file=buf)
        print("  stuck task stack:\n" + "\n".join("    " + l for l in buf.getvalue().splitlines()))
        # prove the request was merely left paused: continue it from the loop thread
        rid = paused_ids[-1]
        await asyncio.wait_for(tab.send(cdp.fetch.continue_request(request_id=rid)), 5)
        done2, _ = await asyncio.wait({nav}, timeout=8)
        print(f"  after manual Fetch.continueRequest({rid}) from loop thread: navigate done={nav in done2}")
        if nav not in done2:
            nav.cancel()
            try:
                await nav
            except BaseException:
                pass
    for e in errors:
        print("  loop error:", e)
    tab.remove_handlers()
    try:
        await asyncio.wait_for(tab.send(cdp.fetch.disable()), 5)
    except Exception as e:
        print("  fetch.disable:", e)
    await asyncio.wait_for(tab.close(), 10)

async def main():
    srv = serve()
    url = f"http://127.0.0.1:{srv.server_address[1]}/page"
    browser = await zendriver.start(headless=True)
    print("browser pid", browser._process_pid)
    try:
        for kind in sys.argv[1:] or ["async", "sync", "lambda-conn"]:
            print("==", kind)
            await asyncio.wait_for(run(kind, browser, url), 60)
    finally:
        await browser.stop()
        srv.shutdown()

asyncio.run(main())
