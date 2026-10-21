"""Real-Chromium probe: feed_cdp from sync vs async RequestPaused handlers.

usage: python probe_fetch.py <variant>
variants: async_def, sync_def, sync_lambda, sync_def_threadsafe
"""
import asyncio
import http.server
import sys
import threading
import time

import zendriver
from zendriver import cdp

print("zendriver from", zendriver.__file__, "python", sys.version.split()[0])

VARIANT = sys.argv[1]


class H(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        body = b"<html><title>OK</title><body>hello</body></html>"
        self.send_response(200)
        self.send_header("Content-Type", "text/html")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *a):
        pass


async def main() -> None:
    srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), H)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    base = f"http://127.0.0.1:{srv.server_address[1]}"

    loop = asyncio.get_running_loop()
    loop_errors: list[str] = []

    def exc_handler(lp, ctx):
        loop_errors.append(f"{ctx.get('message')} | {ctx.get('exception')!r}")

    loop.set_exception_handler(exc_handler)

    browser = await zendriver.start(headless=True)
    try:
        tab = await browser.get(base + "/start")
        paused: list[str] = []
        threads: list[str] = []
        handler_errors: list[str] = []

        if VARIANT == "async_def":

            async def on_paused(ev: cdp.fetch.RequestPaused, conn) -> None:
                threads.append(threading.current_thread().name)
                paused.append((ev.request_id, ev.request.url))
                conn.feed_cdp(cdp.fetch.continue_request(request_id=ev.request_id))

            tab.add_handler(cdp.fetch.RequestPaused, on_paused)
        elif VARIANT == "sync_def":

            def on_paused(ev: cdp.fetch.RequestPaused, conn) -> None:
                threads.append(threading.current_thread().name)
                paused.append((ev.request_id, ev.request.url))
                try:
                    conn.feed_cdp(cdp.fetch.continue_request(request_id=ev.request_id))
                except Exception as e:
                    handler_errors.append(repr(e))
                    raise

            tab.add_handler(cdp.fetch.RequestPaused, on_paused)
        elif VARIANT == "sync_lambda":
            tab.add_handler(
                cdp.fetch.RequestPaused,
                lambda ev, t: (
                    paused.append((ev.request_id, ev.request.url)),
                    threads.append(threading.current_thread().name),
                    t.feed_cdp(cdp.fetch.continue_request(request_id=ev.request_id)),
                ),
            )
        elif VARIANT == "sync_def_threadsafe":
            # workaround a user could write today
            def on_paused(ev: cdp.fetch.RequestPaused, conn) -> None:
                threads.append(threading.current_thread().name)
                paused.append((ev.request_id, ev.request.url))
                asyncio.run_coroutine_threadsafe(
                    conn.send(cdp.fetch.continue_request(request_id=ev.request_id)),
                    loop,
                )

            tab.add_handler(cdp.fetch.RequestPaused, on_paused)

        await tab.send(cdp.fetch.enable())
        t0 = time.monotonic()
        try:
            pre = await tab.send(cdp.runtime.evaluate("String(window.__r)"))
            res = await asyncio.wait_for(
                tab.send(
                    cdp.runtime.evaluate(
                        f"window.__r='pending'; fetch('{base}/x').then(r=>{{window.__r=r.status; return r.status}})", await_promise=True
                    )
                ),
                8,
            )
            print(f"[{VARIANT}] fetch completed status={res[0].value} after {time.monotonic()-t0:.2f}s")
        except asyncio.TimeoutError:
            print(f"[{VARIANT}] fetch HUNG >8s; paused ids={paused} threads={threads}")
            # Chrome behaviour check: is the request still paused? Wait longer, then continue manually
            res = await tab.send(cdp.runtime.evaluate("String(window.__r)"))
            print(f"[{VARIANT}] at 8s window.__r={res[0].value}")
            await asyncio.sleep(20)
            res = await tab.send(cdp.runtime.evaluate("String(window.__r)"))
            print(f"[{VARIANT}] at 28s window.__r={res[0].value}")
            if paused:
                t1 = time.monotonic()
                for rid, _u in paused:
                    await tab.send(cdp.fetch.continue_request(request_id=rid))
                await asyncio.sleep(1)
                res = await tab.send(cdp.runtime.evaluate("String(window.__r)"))
                print(f"[{VARIANT}] manual continue after 28s accepted by Chrome; fetch result now={res[0].value}")
        await asyncio.sleep(0.5)
        import gc

        gc.collect()
        await asyncio.sleep(0.1)
        print(f"[{VARIANT}] handler threads={threads} handler_errors={handler_errors}")
        print(f"[{VARIANT}] loop errors={loop_errors}")
    finally:
        await browser.stop()
        srv.shutdown()


asyncio.run(main())
