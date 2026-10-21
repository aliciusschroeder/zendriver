import asyncio
import http.server
import threading
import sys
import logging

import zendriver as zd
from zendriver import cdp

print("zendriver from", zd.__file__, sys.version.split()[0])


class H(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        body = f"<html><body>{self.path}</body></html>".encode()
        self.send_response(200)
        self.send_header("Content-Type", "text/html")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *a):
        pass


srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), H)
threading.Thread(target=srv.serve_forever, daemon=True).start()
BASE = f"http://127.0.0.1:{srv.server_address[1]}"


def spy(tab, log):
    orig = tab._send_transaction

    async def wrapped(tx):
        log.append((tx.method, tx.params))
        return await orig(tx)

    tab._send_transaction = wrapped


async def raw_paused_counter(tab, store):
    # count Fetch.requestPaused frames independently of zendriver handlers by
    # wrapping the session inbox / receive
    orig = tab._receive_message

    async def wrapped():
        m = await orig()
        if m and m.get("method") == "Fetch.requestPaused":
            store.append(m["params"]["request"]["url"])
        return m

    tab._receive_message = wrapped


async def case_a12_2(browser):
    print("\n=== A12.2: remove handler leaves Fetch enabled ===")
    tab = await browser.get("about:blank", new_tab=True)
    sent = []
    spy(tab, sent)
    raw = []
    await raw_paused_counter(tab, raw)
    seen = []

    async def h(ev: cdp.fetch.RequestPaused, conn):
        seen.append(ev.request.url)
        await conn.send(cdp.fetch.continue_request(request_id=ev.request_id))

    tab.add_handler(cdp.fetch.RequestPaused, h)
    await asyncio.wait_for(tab.get(BASE + "/one"), 15)
    print("with handler: seen", seen, "enabled", [m.__name__ for m in tab.enabled_domains])
    tab.remove_handlers(cdp.fetch.RequestPaused, h)
    raw.clear()
    sent.clear()
    try:
        await asyncio.wait_for(tab.get(BASE + "/two", timeout=5), 8)
        print("second nav OK")
    except asyncio.TimeoutError:
        print("second nav TimeoutError")
    print("sent during second nav:", [m for m, _ in sent])
    print("raw Fetch.requestPaused frames after remove:", raw)
    print("enabled", tab.enabled_domains, "manual", tab.manually_enabled_domains)
    try:
        r = await asyncio.wait_for(tab.evaluate("location.href"), 5)
        print("evaluate ->", r)
    except asyncio.TimeoutError:
        print("evaluate TimeoutError")
    # cleanup: disable fetch so the tab can close
    await asyncio.wait_for(tab.send(cdp.fetch.disable()), 5)
    await tab.close()


async def case_a2_2(browser, continue_all):
    print(f"\n=== A2.2: manual disable re-enabled (handler continues all={continue_all}) ===")
    tab = await browser.get("about:blank", new_tab=True)
    sent = []
    spy(tab, sent)
    raw = []
    await raw_paused_counter(tab, raw)
    seen = []

    async def h(ev: cdp.fetch.RequestPaused, conn):
        seen.append(ev.request.url)
        if continue_all or ev.request.url.endswith("/x"):
            await conn.send(cdp.fetch.continue_request(request_id=ev.request_id))

    tab.add_handler(cdp.fetch.RequestPaused, h)
    await tab.send(cdp.fetch.enable(patterns=[cdp.fetch.RequestPattern(url_pattern="*/x")]))
    print("after enable: enabled", tab.enabled_domains, "manual", [m.__name__ for m in tab.manually_enabled_domains])
    await asyncio.wait_for(tab.get(BASE + "/a", timeout=5), 8)
    print("nav /a while pattern */x active: seen", seen)
    await tab.send(cdp.fetch.disable())
    print("after disable: enabled", tab.enabled_domains, "manual", tab.manually_enabled_domains)
    sent.clear()
    raw.clear()
    seen.clear()
    try:
        await asyncio.wait_for(tab.send(cdp.page.navigate(BASE + "/b")), 5)
        await tab.wait()
        print("navigate /b OK")
    except asyncio.TimeoutError:
        print("navigate /b TimeoutError")
    print("sent after disable:", sent)
    print("raw paused after disable:", raw, "handler seen", seen)
    await asyncio.wait_for(tab.send(cdp.fetch.disable()), 5)
    tab.remove_handlers()
    await tab.close()


async def main():
    browser = await zd.start(headless=True)
    try:
        await case_a12_2(browser)
        await case_a2_2(browser, continue_all=False)
        await case_a2_2(browser, continue_all=True)
    finally:
        await browser.stop()
        srv.shutdown()


asyncio.run(main())
