"""Q6 refute probe: real headless Chromium, expect_request/expect_response pairing.

Usage: python real_probe.py <scenario> <trials>
scenario: imgs8 | fetch2 | single
"""

import asyncio
import gc
import http.server
import sys
import threading

import zendriver
from zendriver import cdp

print("zendriver from", zendriver.__file__, "python", sys.version.split()[0])

PNG = bytes.fromhex(
    "89504e470d0a1a0a0000000d4948445200000001000000010806000000"
    "1f15c4890000000d49444154789c6360000002000154a24f5d0000000049454e44ae426082"
)


class H(http.server.BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def do_GET(self):
        p = self.path
        if p.startswith("/imgs8.html"):
            body = (
                "<html><body>"
                + "".join(f'<img src="/img{i}.png?t={p[-6:]}">' for i in range(8))
                + "</body></html>"
            ).encode()
            ct = "text/html"
        elif p.startswith("/fetch2.html"):
            body = (
                "<html><body><script>"
                "Promise.all([fetch('/a.json?'+Math.random()).then(r=>r.text()),fetch('/b.json?'+Math.random()).then(r=>r.text())])"
                "</script></body></html>"
            ).encode()
            ct = "text/html"
        elif p.startswith("/single.html"):
            body = b"<html><body><img src='/img0.png?x'><script>fetch('/a.json?'+Math.random()).then(r=>r.text())</script></body></html>"
            ct = "text/html"
        elif ".png" in p:
            body = PNG
            ct = "image/png"
        elif ".json" in p:
            body = ('{"path": "%s"}' % p).encode()
            ct = "application/json"
        else:
            self.send_response(404)
            self.end_headers()
            return
        self.send_response(200)
        self.send_header("Content-Type", ct)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)


async def main(scenario: str, trials: int) -> None:
    srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), H)
    th = threading.Thread(target=srv.serve_forever, daemon=True)
    th.start()
    base = f"http://127.0.0.1:{srv.server_address[1]}"

    loop = asyncio.get_running_loop()
    errors: list[str] = []

    def handler(loop, ctx):
        errors.append(repr(ctx.get("exception")) + " | " + ctx.get("message", ""))

    loop.set_exception_handler(handler)

    pattern = {
        "imgs8": r".*/img\d+\.png.*",
        "fetch2": r".*\.json.*",
        "single": r".*/a\.json.*",
    }[scenario]

    browser = await zendriver.start(headless=True)
    mismatches = 0
    try:
        tab = browser.main_tab
        assert tab is not None
        for t in range(trials):
            async with tab.expect_request(pattern) as exp:
                await tab.get(f"{base}/{scenario}.html?n={t:06d}")
                req = await asyncio.wait_for(exp.value, 15)
                resp = await asyncio.wait_for(exp.response_future, 15)
                body, _ = await asyncio.wait_for(exp.response_body, 15)
            ok = req.request_id == resp.request_id
            if not ok:
                mismatches += 1
            print(
                f"trial {t}: request={req.request.url.rsplit('/',1)[-1]} "
                f"response={resp.response.url.rsplit('/',1)[-1]} "
                f"exp.request_id={exp.request_id} req_id={req.request_id} "
                f"body={body[:40]!r} {'OK' if ok else 'MISMATCH'}"
            )
            await asyncio.sleep(0.2)
    finally:
        await browser.stop()
        srv.shutdown()
    gc.collect()
    await asyncio.sleep(0.1)
    gc.collect()
    print(f"scenario={scenario} mismatches={mismatches}/{trials}")
    print(f"loop exception handler calls: {len(errors)}")
    for e in errors[:3]:
        print("  ", e)


if __name__ == "__main__":
    asyncio.run(main(sys.argv[1], int(sys.argv[2])))
