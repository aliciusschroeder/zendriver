import asyncio, time, http.server, threading
import zendriver as zd
from zendriver import cdp

class H(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/slow":
            time.sleep(2)
            body = b"<title>slow</title><p id=new>new page</p>"
        else:
            body = b"<title>a</title><p id=old>old</p><script>let i=0;setInterval(()=>{document.title='t'+(i++)},20)</script>"
        self.send_response(200); self.send_header("Content-Type","text/html"); self.send_header("Content-Length", str(len(body))); self.end_headers(); self.wfile.write(body)
    def log_message(self, *a): pass
srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), H)
threading.Thread(target=srv.serve_forever, daemon=True).start()
B = f"http://127.0.0.1:{srv.server_address[1]}"

async def main():
    b = await zd.start(headless=True)
    try:
        tab = await b.get(B + "/a")
        await asyncio.sleep(0.5)
        t = time.time()
        tab = await b.get(B + "/slow", timeout=5)
        print(f"get(/slow) returned after {time.time()-t:.2f}s; location now:", await tab.evaluate("location.href"))
        # raw: how long does Page.navigate take?
        await b.get(B + "/a"); await asyncio.sleep(0.3)
        t = time.time()
        await tab.send(cdp.page.navigate(B + "/slow"))
        print(f"raw Page.navigate replied after {time.time()-t:.2f}s; location:", await tab.evaluate("location.href"))
    finally:
        await b.stop()
asyncio.run(main())
