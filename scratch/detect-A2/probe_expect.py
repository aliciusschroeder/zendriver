import asyncio, threading, http.server
import zendriver as zd
from zendriver import cdp

PNG = bytes.fromhex("89504e470d0a1a0a0000000d49484452000000010000000108060000001f15c4890000000d49444154789c6360000002000154a24f5d0000000049454e44ae426082")
class H(http.server.BaseHTTPRequestHandler):
    def log_message(self, *a): pass
    def do_GET(self):
        if self.path.startswith("/page"):
            body = b"<html>" + b"".join(b'<img src="/img%d.png">' % i for i in range(8)) + b"</html>"; ct = "text/html"
        else:
            body = PNG; ct = "image/png"
        self.send_response(200); self.send_header("Content-Type", ct); self.send_header("Cache-Control", "no-store"); self.send_header("Content-Length", str(len(body))); self.end_headers(); self.wfile.write(body)

errors = []
async def main():
    asyncio.get_running_loop().set_exception_handler(lambda l, c: errors.append(repr(c.get("exception"))))
    srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), H)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    base = f"http://127.0.0.1:{srv.server_address[1]}"
    browser = await zd.start(headless=True)
    mism = 0
    try:
        tab = await browser.get("about:blank")
        for i in range(10):
            async with tab.expect_request(r".*/img\d\.png") as req:
                await tab.get(base + f"/page{i}")
                rq = (await asyncio.wait_for(req.request, 5)).url
                rs = (await asyncio.wait_for(req.response, 5)).url
                if rq != rs:
                    mism += 1
                    print("MISMATCH request", rq, "response", rs)
    finally:
        await browser.stop()
    import gc; gc.collect()
    print("mismatches:", mism, "loop errors:", errors[:3], len(errors))

asyncio.run(asyncio.wait_for(main(), 80))
