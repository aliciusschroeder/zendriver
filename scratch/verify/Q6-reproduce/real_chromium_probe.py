"""Q6 reproducer against real headless Chromium.

Serves a local page with many matching subresources, then checks whether
expect_request / expect_response pair the request with a different request's
response / body, and counts lost InvalidStateError task exceptions.
"""

import asyncio
import re
import base64
import http.server
import sys
import threading
import urllib.parse

import zendriver as zd
from zendriver import cdp

PNG = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAChwGA60e6kgAAAABJRU5ErkJggg=="
)


class H(http.server.BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def do_GET(self):
        u = urllib.parse.urlparse(self.path)
        q = urllib.parse.parse_qs(u.query)
        if u.path == "/imgs":
            n = int(q.get("n", ["20"])[0])
            t = q.get("t", ["0"])[0]
            body = "<html><body>" + "".join(
                f'<img src="/img{i}.png?t={t}">' for i in range(n)
            ) + "</body></html>"
            self._send(body.encode(), "text/html")
        elif u.path.startswith("/img"):
            self._send(PNG, "image/png", nocache=True)
        elif u.path == "/fetches":
            n = int(q.get("n", ["5"])[0])
            t = q.get("t", ["0"])[0]
            js = "Promise.all([" + ",".join(
                f"fetch('/data?n={i}&t={t}').then(r => r.text())" for i in range(n)
            ) + "])"
            body = f"<html><body><script>{js}</script></body></html>"
            self._send(body.encode(), "text/html")
        elif u.path == "/data":
            self._send(f"payload for {self.path}".encode(), "text/plain", nocache=True)
        else:
            self.send_response(404)
            self.end_headers()

    def _send(self, data, ctype, nocache=False):
        self.send_response(200)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        if nocache:
            self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(data)


async def trial(tab, kind, url, pattern):
    cls = tab.expect_request if kind == "request" else tab.expect_response
    log = []
    def logger_(ev):
        if re.fullmatch(pattern, getattr(getattr(ev, "request", None), "url", "") or "") or type(ev).__name__ != "RequestWillBeSent":
            log.append((type(ev).__name__, ev.request_id))
    for et in (cdp.network.RequestWillBeSent, cdp.network.ResponseReceived, cdp.network.LoadingFinished, cdp.network.LoadingFailed):
        tab.add_handler(et, logger_)
    async with cls(pattern) as exp:
        await tab.get(url)
        req_ev = await asyncio.wait_for(exp.request_future, 10)
        resp_ev = await asyncio.wait_for(exp.response_future, 10)
        try:
            body, _ = await asyncio.wait_for(exp.response_body, 10)
        except TimeoutError:
            print("TIMEOUT response_body", kind, url, "req_id", req_ev.request_id, "attr", exp.request_id, "resp", resp_ev.request_id, "lf done", exp.loading_finished_future.done())
            print("  handlers LF:", tab.handlers[cdp.network.LoadingFinished])
            print("  log:", [l for l in log])
            body = "TIMEOUT"
    for et in (cdp.network.RequestWillBeSent, cdp.network.ResponseReceived, cdp.network.LoadingFinished, cdp.network.LoadingFailed):
        tab.remove_handlers(et, logger_)
    if True:
        val = await asyncio.wait_for(exp.value, 10)
        await tab.wait_for_ready_state("complete")
    return {
        "req_url": req_ev.request.url,
        "req_id": req_ev.request_id,
        "attr_id": exp.request_id,
        "resp_url": resp_ev.response.url,
        "resp_id": resp_ev.request_id,
        "value_type": type(val).__name__,
        "value_url": (val.request.url if hasattr(val, "request") else val.response.url),
        "body": body[:40] if ("payload" in body or body == "TIMEOUT") else len(body),
    }


async def main():
    print("python", sys.version.split()[0], "zendriver", zd.__file__)
    srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), H)
    port = srv.server_address[1]
    threading.Thread(target=srv.serve_forever, daemon=True).start()

    loop = asyncio.get_running_loop()
    errors = []

    def exc_handler(loop, ctx):
        errors.append(repr(ctx.get("exception")) + " | " + ctx.get("message", ""))

    loop.set_exception_handler(exc_handler)

    browser = await zd.start(headless=True)
    try:
        tab = browser.main_tab
        results = {"request-imgs": [], "response-imgs": [], "request-fetch": [], "response-fetch": []}
        for t in range(5):
            r = await trial(tab, "request", f"http://127.0.0.1:{port}/imgs?n=30&t=a{t}", r".*/img\d+\.png\?t=.*")
            results["request-imgs"].append(r)
            r = await trial(tab, "response", f"http://127.0.0.1:{port}/imgs?n=30&t=b{t}", r".*/img\d+\.png\?t=.*")
            results["response-imgs"].append(r)
            r = await trial(tab, "request", f"http://127.0.0.1:{port}/fetches?n=5&t=c{t}", r".*/data\?n=.*")
            r["body"] = r["body"]
            results["request-fetch"].append(r)
            r = await trial(tab, "response", f"http://127.0.0.1:{port}/fetches?n=5&t=d{t}", r".*/data\?n=.*")
            results["response-fetch"].append(r)
        # let unobserved task exceptions be collected
        import gc

        await asyncio.sleep(0.5)
        gc.collect()
        await asyncio.sleep(0.1)
        for k, rs in results.items():
            mism = 0
            for r in rs:
                ok = r["req_id"] == r["resp_id"] == r["attr_id"]
                mism += not ok
                print(
                    f"{k}: {'OK      ' if ok else 'MISMATCH'} req={r['req_url'].split('/')[-1]}({r['req_id']}) "
                    f"attr_id={r['attr_id']} resp={r['resp_url'].split('/')[-1]}({r['resp_id']}) "
                    f"value={r['value_type']}:{r['value_url'].split('/')[-1]} body={r['body']!r}"
                )
            print(f"== {k}: mismatches {mism}/{len(rs)}")
        ise = [e for e in errors if "InvalidStateError" in e]
        print("loop exception handler calls:", len(errors), "InvalidStateError:", len(ise))
        if errors:
            print("sample:", errors[0])
    finally:
        await browser.stop()
        srv.shutdown()


asyncio.run(main())
