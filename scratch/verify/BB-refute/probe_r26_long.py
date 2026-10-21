import asyncio, http.server, threading, sys, time
import zendriver as zd
from zendriver import cdp
print("zendriver from", zd.__file__, sys.version.split()[0])
class H(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        b=b"<html>ok</html>"; self.send_response(200); self.send_header("Content-Length",str(len(b))); self.end_headers(); self.wfile.write(b)
    def log_message(self,*a): pass
srv=http.server.ThreadingHTTPServer(("127.0.0.1",0),H); threading.Thread(target=srv.serve_forever,daemon=True).start()
BASE=f"http://127.0.0.1:{srv.server_address[1]}"
async def main():
    browser=await zd.start(headless=True)
    try:
        tab=browser.main_tab
        async def h(ev, conn):
            await conn.send(cdp.fetch.continue_request(request_id=ev.request_id))
        tab.add_handler(cdp.fetch.RequestPaused, h)
        await tab.get(BASE+"/one")
        tab.remove_handlers()
        t0=time.monotonic()
        nav=asyncio.ensure_future(tab.send(cdp.page.navigate(BASE+"/two")))
        try:
            await asyncio.wait_for(asyncio.shield(nav), 45)
            print("navigate returned after", round(time.monotonic()-t0,1), "s")
        except asyncio.TimeoutError:
            print("Page.navigate still pending after 45s")
            print("stack of the stuck send:"); nav.print_stack(limit=3)
        await asyncio.wait_for(tab.send(cdp.fetch.disable()), 10)
        await asyncio.wait_for(asyncio.shield(nav), 10)
        print("after manual Fetch.disable navigate returned:", nav.done())
    finally:
        await browser.stop(); srv.shutdown()
asyncio.run(main())
