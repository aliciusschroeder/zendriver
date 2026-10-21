import asyncio
import http.server
import threading

import zendriver
from zendriver import cdp

print("zendriver imported from:", zendriver.__file__)

HITS: dict[str, int] = {}


def start_http() -> tuple[http.server.ThreadingHTTPServer, str]:
    class H(http.server.BaseHTTPRequestHandler):
        def do_GET(self) -> None:
            HITS[self.path] = HITS.get(self.path, 0) + 1
            body = b"<html><body>hi</body></html>"
            self.send_response(200)
            self.send_header("Content-Type", "text/html")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, *a: object) -> None:
            pass

    srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), H)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv, f"http://127.0.0.1:{srv.server_address[1]}/"


def names(tab: zendriver.Tab) -> list[str]:
    return [m.__name__.rsplit(".", 1)[-1] for m in tab.enabled_domains]


async def main() -> None:
    srv, url = start_http()
    browser = await zendriver.start(headless=True)
    try:
        tab = await browser.get(url + "a")

        def h(ev: object) -> None:
            pass

        # B14.1: network -> runtime swap, marker shows whether the command ran
        tab.add_handler(cdp.network.RequestWillBeSent, h)
        await tab.evaluate("1")
        tab.remove_handlers(cdp.network.RequestWillBeSent, h)
        consoles: list[object] = []
        tab.add_handler(cdp.runtime.ConsoleAPICalled, lambda ev: consoles.append(ev))
        try:
            r = await tab.evaluate("window.__m = 42; console.log('x'); 2")
            print("B14.1 OK ->", r, names(tab))
        except Exception as e:
            print("B14.1 RAISED", type(e).__name__, e)
        await asyncio.sleep(0.5)
        print("B14.1 marker", await tab.evaluate("window.__m"), "consoles", len(consoles))
        tab.remove_handlers()
        await tab.evaluate("0")
        print("converged", names(tab))

        # A2.1 log variant with raw send
        tab.add_handler(cdp.network.RequestWillBeSent, h)
        await tab.send(cdp.runtime.evaluate("1"))
        tab.remove_handlers(cdp.network.RequestWillBeSent, h)
        tab.add_handler(cdp.log.EntryAdded, h)
        try:
            await tab.send(cdp.runtime.evaluate("window.__m2 = 7"))
            print("A2.1 log OK", names(tab), "marker", await tab.evaluate("window.__m2"))
        except Exception as e:
            print("A2.1 log RAISED", type(e).__name__, e)
        tab.remove_handlers()
        await tab.evaluate("0")

        # stale network + two new domains at once (nested pass enables a second one)
        tab.add_handler(cdp.network.RequestWillBeSent, h)
        await tab.evaluate("1")
        tab.remove_handlers(cdp.network.RequestWillBeSent, h)
        tab.add_handler(cdp.page.LoadEventFired, h)
        tab.add_handler(cdp.log.EntryAdded, h)
        try:
            await tab.evaluate("window.__m3 = 9")
            print("two-new OK", sorted(names(tab)), "marker", await tab.evaluate("window.__m3"))
        except Exception as e:
            print("two-new RAISED", type(e).__name__, e)
        tab.remove_handlers()
        await tab.evaluate("0")
        print("converged", names(tab))

        # A2.1 expect_request then LoadEventFired handler then reload
        async with tab.expect_request(url + "a") as req:
            await tab.reload()
            await asyncio.wait_for(req.value, 10)
        print("after expect_request", names(tab))
        loads: list[object] = []
        tab.add_handler(cdp.page.LoadEventFired, lambda ev: loads.append(ev))
        before = HITS.get("/a", 0)
        try:
            await tab.reload()
            await asyncio.sleep(1)
            print("A2.1 reload OK", names(tab), "hits", before, "->", HITS.get("/a"), "loads", len(loads))
        except Exception as e:
            print("A2.1 reload RAISED", type(e).__name__, e)
        tab.remove_handlers()
        await tab.evaluate("0")

        # B14.1 expect_response around get, then LoadEventFired handler, reload
        async with tab.expect_response(url + "b"):
            await tab.get(url + "b")
        print("after expect_response", names(tab))
        loads.clear()
        tab.add_handler(cdp.page.LoadEventFired, lambda ev: loads.append(ev))
        before = HITS.get("/b", 0)
        try:
            await tab.reload()
            await asyncio.sleep(1)
            print("B14.1 reload OK", names(tab), "hits", before, "->", HITS.get("/b"), "loads", len(loads))
        except Exception as e:
            print("B14.1 reload RAISED", type(e).__name__, e)
    finally:
        await browser.stop()
        srv.shutdown()


asyncio.run(asyncio.wait_for(main(), 120))
