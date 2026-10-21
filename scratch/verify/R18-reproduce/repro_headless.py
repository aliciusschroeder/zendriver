"""Reproducer for B14.6: a session detached while its first send() is inside
_prepare_headless leaves _prep_headless_done=True, so after reattach the
HeadlessChrome UA override is skipped; plus a Listener is started on the
detached connection.

Real headless Chromium. Usage: python repro_headless.py <race 0|1>
"""
import asyncio
import gc
import http.server
import sys
import threading

import zendriver as zd
import zendriver.core.connection as zc

print("zendriver from", zd.__file__, "python", sys.version.split()[0])
RACE = int(sys.argv[1])


class H(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        body = ("UA-HEADER:" + self.headers.get("user-agent", "")).encode()
        self.send_response(200)
        self.send_header("content-type", "text/plain")
        self.send_header("content-length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *a):
        pass


srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), H)
threading.Thread(target=srv.serve_forever, daemon=True).start()
URL = f"http://127.0.0.1:{srv.server_address[1]}/ua"

zombies = []
_orig_init = zc.Listener.__init__


def rec_init(self, connection):
    if connection.websocket is None and connection._inbox is None:
        import traceback

        zombies.append("".join(traceback.format_stack(limit=4)[:-1]))
    _orig_init(self, connection)


zc.Listener.__init__ = rec_init

loop_errors = []


async def main():
    asyncio.get_running_loop().set_exception_handler(
        lambda loop, ctx: loop_errors.append(
            f"{ctx.get('message')} | {ctx.get('exception')!r}"
        )
    )
    browser = await zd.start(headless=True)
    try:
        tab = await browser.get("about:blank", new_tab=True)
        assert tab.session_id is None

        if RACE:

            async def closer():
                while tab.session_id is None:
                    await asyncio.sleep(0)
                print(
                    "closer: session attached, _prep_headless_done =",
                    tab.__dict__.get("_prep_headless_done"),
                )
                await tab.aclose()

            res = await asyncio.wait_for(
                asyncio.gather(tab.evaluate("1"), closer(), return_exceptions=True),
                30,
            )
            print("first send result:", [repr(r)[:90] for r in res])
        else:
            print("first send result:", await tab.evaluate("1"))
            await tab.aclose()
        print(
            "after detach: session_id =",
            tab.session_id,
            "_prep_headless_done =",
            tab.__dict__.get("_prep_headless_done"),
            "listener.running =",
            tab.listener.running if tab.listener else None,
            "mapper =",
            dict(tab.mapper),
        )
        await asyncio.sleep(0.2)
        # next send reattaches a new session
        ua = await asyncio.wait_for(tab.evaluate("navigator.userAgent"), 30)
        print("navigator.userAgent after reattach:", ua)
        await asyncio.wait_for(tab.get(URL), 30)
        body = await asyncio.wait_for(tab.evaluate("document.body.innerText"), 30)
        print("HTTP header after reattach:", body)
        print("HeadlessChrome leaked:", "HeadlessChrome" in ua, "HeadlessChrome" in body)
        await tab.close()
    finally:
        await browser.stop()
        srv.shutdown()
    gc.collect()
    await asyncio.sleep(0.1)
    print("zombie Listener() calls on a detached connection:", len(zombies))
    for z in zombies[:1]:
        print(z)
    print("loop errors:", len(loop_errors))
    for e in loop_errors:
        print("  ", e[:200])


asyncio.run(main())
