import asyncio, threading, http.server, functools, os, sys, base64
import zendriver as zd

HERE = os.path.dirname(os.path.abspath(__file__))
SITE = os.path.join(HERE, "site")
PNG = base64.b64decode("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAChwGA60e6kgAAAABJRU5ErkJggg==")
for i in range(40):
    open(os.path.join(SITE, f"img{i}.png"), "wb").write(PNG)

class H(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *a): pass
    def do_GET(self):
        if self.path.startswith("/index.html"):
            q = self.path.split("?",1)[1] if "?" in self.path else "0"
            body = "<html><body>" + "".join(f'<img src="/img{i}.png?t={q}">' for i in range(40)) + "</body></html>"
            b = body.encode()
            self.send_response(200); self.send_header("Content-Type","text/html"); self.send_header("Content-Length", str(len(b))); self.end_headers(); self.wfile.write(b)
            return
        if self.path.startswith("/img"):
            self.path = self.path.split("?")[0]
        return super().do_GET()

srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), functools.partial(H, directory=SITE))
port = srv.server_address[1]
threading.Thread(target=srv.serve_forever, daemon=True).start()

async def main():
    loop = asyncio.get_running_loop()
    errors = []
    loop.set_exception_handler(lambda l, ctx: errors.append(repr(ctx.get("exception"))))
    browser = await zd.start(headless=True, browser_connection_timeout=1.0, browser_connection_max_tries=30)
    tab = browser.main_tab
    mismatches = 0
    for trial in range(8):
        async with tab.expect_request(r".*/img\d+\.png\?t=.*") as exp:
            await tab.get(f"http://127.0.0.1:{port}/index.html?{trial}")
            req = await asyncio.wait_for(exp.request, 10)
            try:
                resp = await asyncio.wait_for(exp.response, 10)
                rurl = resp.url
            except asyncio.TimeoutError:
                rurl = "<response TIMEOUT>"
            ok = req.url == rurl
            mismatches += (not ok)
            print(trial, "request:", req.url.split("/")[-1], "response:", rurl.split("/")[-1], "OK" if ok else "MISMATCH")
    import gc; gc.collect(); await asyncio.sleep(0.2)
    print("mismatches", mismatches, "loop errors:", len(errors), errors[:2])
    await browser.stop()

asyncio.run(main())
