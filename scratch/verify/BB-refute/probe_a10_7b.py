import asyncio, http.server, threading, sys
import zendriver as zd
from zendriver import cdp
print("zendriver from", zd.__file__, sys.version.split()[0])
POLL=b"<html><body><script>setInterval(()=>fetch('/pollreq?'+Date.now()),300)</script></body></html>"
class H(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        b=POLL if self.path=="/poll" else b"ok"; self.send_response(200); self.send_header("Content-Length",str(len(b))); self.end_headers(); self.wfile.write(b)
    def log_message(self,*a): pass
srv=http.server.ThreadingHTTPServer(("127.0.0.1",0),H); threading.Thread(target=srv.serve_forever,daemon=True).start()
BASE=f"http://127.0.0.1:{srv.server_address[1]}"
async def main():
    browser=await zd.start(headless=True)
    try:
        tab=browser.main_tab
        # earlier, unrelated use of expect_* with a send inside the block
        async with tab.expect_response(r".*/other") as e:
            await tab.get(BASE+"/other")
            await asyncio.wait_for(e.value, 5)
        await tab.get(BASE+"/poll")   # this send drops network from enabled_domains (no Network.disable)
        print("enabled_domains before 2nd block:", tab.enabled_domains)
        async with tab.expect_request(r".*/pollreq.*") as r:
            try:
                ev=await asyncio.wait_for(asyncio.shield(r.value), 4)
                print("2nd block, pure await resolved:", ev.request.url)
            except asyncio.TimeoutError:
                print("2nd block, pure await: nothing after 4s")
    finally:
        await browser.stop(); srv.shutdown()
asyncio.run(main())
