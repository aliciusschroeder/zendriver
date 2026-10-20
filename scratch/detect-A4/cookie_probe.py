import asyncio, http.server, threading, os, tempfile, pathlib
import zendriver as zd
from zendriver import cdp

class H(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        body = ("<html><body>cookie header: %s</body></html>" % self.headers.get("Cookie")).encode()
        self.send_response(200)
        if self.path.startswith("/set"):
            self.send_header("Set-Cookie", "hostonly=1; Path=/")
            self.send_header("Set-Cookie", "persist=2; Path=/; Max-Age=3600")
        self.send_header("Content-Type","text/html"); self.send_header("Content-Length", str(len(body))); self.end_headers(); self.wfile.write(body)
    def log_message(self, *a): pass
srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), H)
threading.Thread(target=srv.serve_forever, daemon=True).start()
P = srv.server_address[1]

def show(label, cookies):
    print(label, sorted((c.name, c.domain, c.session, round(c.expires)) for c in cookies))

async def main():
    b = await zd.start(headless=True, browser_args=["--host-resolver-rules=MAP *.test 127.0.0.1"])
    try:
        tab = await b.get(f"http://www.example.test:{P}/set")
        await asyncio.sleep(0.5)
        show("before save:", await b.cookies.get_all())
        f = pathlib.Path(tempfile.mkdtemp()) / "c.dat"
        await b.cookies.save(f)
        await b.cookies.clear()
        await b.cookies.load(f)
        show("after load: ", await b.cookies.get_all())
        sub = await b.get(f"http://sub.www.example.test:{P}/")
        await asyncio.sleep(0.3)
        print("subdomain sees:", await sub.evaluate("document.body.innerText"))
        # site sets host-only cookie again -> duplicates?
        await b.get(f"http://www.example.test:{P}/set")
        await asyncio.sleep(0.3)
        show("after site re-sets:", await b.cookies.get_all())
        t = await b.get(f"http://www.example.test:{P}/")
        await asyncio.sleep(0.3)
        print("origin sees:", await t.evaluate("document.body.innerText"))
    finally:
        await b.stop()
asyncio.run(main())
