"""Q7 reproducer against real headless Chromium."""
import asyncio
import http.server
import sys
import threading
import traceback

import zendriver
from zendriver import cdp

print("zendriver from:", zendriver.__file__, "python", sys.version.split()[0])


class H(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        body = b"<html><body><script>console.log('hi')</script>hello</body></html>"
        self.send_response(200)
        self.send_header("Content-Type", "text/html")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *a):
        pass


srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), H)
threading.Thread(target=srv.serve_forever, daemon=True).start()
URL = f"http://127.0.0.1:{srv.server_address[1]}/page.html"


def names(t):
    return [m.__name__.rsplit(".", 1)[-1] for m in t.enabled_domains]


async def attempt(label, coro):
    try:
        r = await asyncio.wait_for(coro, 20)
        print(f"  [{label}] OK -> {r!r}")
        return True
    except Exception as e:
        print(f"  [{label}] RAISED {type(e).__name__}: {e}")
        traceback.print_exc(limit=-3, file=sys.stdout)
        return False


async def main():
    browser = await zendriver.start(headless=True)
    try:
        # ---- A2.1 / B14.1 direct form
        tab = await browser.get(URL)
        h1 = lambda e: None
        h2 = lambda e: None
        print("== direct: network handler -> evaluate -> swap to runtime handler -> evaluate")
        tab.add_handler(cdp.network.RequestWillBeSent, h1)
        await attempt("evaluate('1')", tab.evaluate("1"))
        print("  enabled_domains:", names(tab))
        tab.remove_handlers(cdp.network.RequestWillBeSent, h1)
        tab.add_handler(cdp.runtime.ConsoleAPICalled, h2)
        await attempt("evaluate('2')", tab.evaluate("2"))
        print("  enabled_domains:", names(tab))
        await attempt("evaluate('3')", tab.evaluate("3"))
        print("  enabled_domains:", names(tab))
        tab.remove_handlers()

        # ---- A2.1 log variant via raw send
        tab2 = await browser.get(URL, new_tab=True)
        print("== direct (log): network handler -> send -> swap to log handler -> send")
        tab2.add_handler(cdp.network.RequestWillBeSent, h1)
        await attempt("send(evaluate 1)", tab2.send(cdp.runtime.evaluate("1")))
        tab2.remove_handlers(cdp.network.RequestWillBeSent, h1)
        tab2.add_handler(cdp.log.EntryAdded, h2)
        await attempt("send(evaluate 1+1)", tab2.send(cdp.runtime.evaluate("1+1")))
        print("  enabled_domains:", names(tab2))

        # ---- public helper: expect_request + reload, then page handler + reload
        tab3 = await browser.get(URL, new_tab=True)
        print("== expect_request then LoadEventFired handler then reload")
        async with tab3.expect_request(URL) as req:
            await tab3.reload()
            r = await asyncio.wait_for(req.request, 20)
            print("  expected request url:", r.url)
        print("  handlers after expect block:", {k.__name__: len(v) for k, v in tab3.handlers.items()})
        print("  enabled_domains:", names(tab3))
        loads = []
        tab3.add_handler(cdp.page.LoadEventFired, lambda e: loads.append(e))
        await attempt("tab.reload()", tab3.reload())
        print("  enabled_domains:", names(tab3))

        # ---- public helper: expect_response + get, then page handler + reload
        tab4 = await browser.get(URL, new_tab=True)
        print("== expect_response(tab.get) then LoadEventFired handler then reload")
        async with tab4.expect_response(URL) as resp:
            await tab4.get(URL)
            rr = await asyncio.wait_for(resp.response, 20)
            print("  expected response status:", rr.status)
        print("  enabled_domains:", names(tab4))
        tab4.add_handler(cdp.page.LoadEventFired, lambda e: None)
        await attempt("tab.reload()", tab4.reload())
        print("  enabled_domains:", names(tab4))
    finally:
        await browser.stop()
        srv.shutdown()


asyncio.run(main())
