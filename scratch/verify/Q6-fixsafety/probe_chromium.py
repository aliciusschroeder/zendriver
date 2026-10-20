import asyncio
import gc
import http.server
import sys
import threading

import zendriver as zd

print("zendriver imported from:", zd.__file__, "| python", sys.version.split()[0])

PNG = bytes.fromhex(
    "89504e470d0a1a0a0000000d4948445200000001000000010806000000"
    "1f15c4890000000d49444154789c6360000002000154a24f5d0000000049454e44ae426082"
)
N = 20


class Handler(http.server.BaseHTTPRequestHandler):
    def log_message(self, *args):  # quiet
        pass

    def do_GET(self):
        if self.path.startswith("/page"):
            body = "".join(
                f'<img src="/img{i}.png?t={self.path}">' for i in range(N)
            ).encode()
            ctype = "text/html"
        else:
            body = PNG
            ctype = "image/png"
        self.send_response(200)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)


async def main() -> None:
    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    port = server.server_address[1]
    errors = []
    loop = asyncio.get_running_loop()
    loop.set_exception_handler(lambda _, ctx: errors.append(repr(ctx.get("exception"))))
    browser = await zd.start(headless=True)
    mismatches = 0
    try:
        tab = browser.main_tab
        for trial in range(5):
            async with tab.expect_request(r".*/img\d+\.png\?t=.*") as exp:
                await tab.get(f"http://127.0.0.1:{port}/page{trial}")
                req = await asyncio.wait_for(exp.value, 10)
                resp = await asyncio.wait_for(exp.response_future, 10)
                body = await asyncio.wait_for(exp.response_body, 10)
                ok = req.request_id == resp.request_id
                mismatches += not ok
                print(
                    f"trial {trial}: request {req.request.url.split('/')[3].split('?')[0]}"
                    f" response {resp.response.url.split('/')[3].split('?')[0]}"
                    f" body_len={len(body[0])} {'OK' if ok else 'MISMATCH'}"
                )
        await asyncio.sleep(0.2)
        gc.collect()
    finally:
        await browser.stop()
        server.shutdown()
    print(f"mismatches: {mismatches}/5, lost task errors: {len(errors)} {sorted(set(errors))}")


asyncio.run(asyncio.wait_for(main(), 100))
