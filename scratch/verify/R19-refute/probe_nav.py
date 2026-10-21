import asyncio, http.server, sys, threading, time
import zendriver
from zendriver import cdp
print("zendriver from", zendriver.__file__, "python", sys.version.split()[0])
class H(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        b=b"<html><title>OK</title></html>"; self.send_response(200); self.send_header("Content-Length",str(len(b))); self.end_headers(); self.wfile.write(b)
    def log_message(self,*a): pass
async def main():
    srv=http.server.ThreadingHTTPServer(("127.0.0.1",0),H); threading.Thread(target=srv.serve_forever,daemon=True).start()
    base=f"http://127.0.0.1:{srv.server_address[1]}"
    asyncio.get_running_loop().set_exception_handler(lambda l,c: None)
    browser=await zendriver.start(headless=True)
    try:
        tab=await browser.get("about:blank")
        kind=sys.argv[1]
        if kind=="sync":
            tab.add_handler(cdp.fetch.RequestPaused, lambda ev, t: t.feed_cdp(cdp.fetch.continue_request(request_id=ev.request_id)))
        else:
            async def h(ev, t): t.feed_cdp(cdp.fetch.continue_request(request_id=ev.request_id))
            tab.add_handler(cdp.fetch.RequestPaused, h)
        await tab.send(cdp.fetch.enable())
        t0=time.monotonic()
        main_task=asyncio.current_task()
        async def watchdog():
            await asyncio.sleep(40)
            print("WATCHDOG: main task stack:", flush=True)
            main_task.print_stack(file=sys.stdout)
            main_task.cancel()
        wd=asyncio.create_task(watchdog())
        try:
            await asyncio.wait_for(tab.get(base+"/page"), 30)
            r=await tab.send(cdp.runtime.evaluate("document.title"))
            print(f"[{kind}] tab.get returned after {time.monotonic()-t0:.1f}s title={r[0].value!r}")
        except asyncio.TimeoutError:
            print(f"[{kind}] tab.get raised TimeoutError after {time.monotonic()-t0:.1f}s", flush=True)
            r=await tab.send(cdp.runtime.evaluate("location.href+' '+document.readyState"))
            print(f"[{kind}] tab.get raised TimeoutError after {time.monotonic()-t0:.1f}s; page={r[0].value!r}")
    finally:
        wd.cancel() if 'wd' in dir() else None
        await browser.stop(); srv.shutdown()
asyncio.run(main())
