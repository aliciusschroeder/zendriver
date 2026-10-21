"""R18 refute lens: does a concurrent first send in expert mode really double-inject
the attachShadow override, and does Chrome then recurse?"""
import asyncio
import http.server
import sys
import threading

import zendriver as zd

print("zendriver from", zd.__file__, "python", sys.version.split()[0])

PAGE = b"""<!doctype html><html><head><title>pending</title></head><body><div id=d></div>
<script>
try { document.getElementById('d').attachShadow({mode:'closed'}); document.title='OK'; }
catch(e) { document.title = 'ERR:' + e; }
</script></body></html>"""


class H(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-Type", "text/html")
        self.end_headers()
        self.wfile.write(PAGE)

    def log_message(self, *a):
        pass


async def run(mode: str, srv_url: str) -> None:
    browser = await zd.start(headless=True, expert=True)
    try:
        ws = browser.connection.websocket
        orig = ws.send
        counter = {"addScript": 0, "uaOverride": 0}

        async def counting_send(msg, *a, **k):
            if "Page.addScriptToEvaluateOnNewDocument" in msg:
                counter["addScript"] += 1
            if "Network.setUserAgentOverride" in msg:
                counter["uaOverride"] += 1
            return await orig(msg, *a, **k)

        ws.send = counting_send  # instance attribute on the websocket, not Connection
        tab = await browser.get(srv_url, new_tab=True)
        before = dict(counter)
        if mode == "seq":
            await tab.evaluate("1")
            await asyncio.gather(tab.evaluate("1"), tab.evaluate("2"))
        elif mode == "gather":
            await asyncio.gather(tab.evaluate("1"), tab.evaluate("2"))
        elif mode == "localstorage":
            await tab.set_local_storage({"a": "1", "b": "2"})
        elif mode == "main_tab_gather":
            tab = browser.tabs[0]
            await tab.get(srv_url)
            await asyncio.gather(tab.evaluate("1"), tab.evaluate("2"))
        await tab.reload()
        await tab.sleep(0.5)
        title = await tab.evaluate("document.title")
        ua = await tab.evaluate("navigator.userAgent")
        print(
            f"mode={mode:16s} addScript sent on tab={counter['addScript'] - before['addScript']} "
            f"uaOverride sent={counter['uaOverride'] - before['uaOverride']} title={title!r} headlessUA={'Headless' in ua}"
        )
    finally:
        await browser.stop()


async def main() -> None:
    srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), H)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    url = f"http://127.0.0.1:{srv.server_address[1]}/"
    for mode in sys.argv[1:] or ["seq", "gather", "localstorage", "main_tab_gather"]:
        await asyncio.wait_for(run(mode, url), 60)
    srv.shutdown()


asyncio.run(main())
