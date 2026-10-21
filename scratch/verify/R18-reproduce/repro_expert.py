"""Reproducer for B14.2: concurrent first sends in expert mode inject the
attachShadow override twice -> RangeError on attachShadow.

Uses the real headless Chromium. Counts Page.addScriptToEvaluateOnNewDocument
messages per session by wrapping websockets' ClientConnection.send (a
websockets class, not Connection).
"""
import asyncio
import collections
import http.server
import json
import sys
import threading

import websockets.asyncio.client as wsc

import zendriver as zd

print("zendriver from", zd.__file__, "python", sys.version.split()[0])

PAGE = b"""<!doctype html><html><head><title>init</title></head><body><script>
try {
  const d = document.createElement('div');
  document.body.appendChild(d);
  d.attachShadow({mode: 'closed'});
  document.title = 'OK';
} catch (e) { document.title = 'ERR:' + e; }
</script></body></html>"""


class H(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("content-type", "text/html")
        self.send_header("content-length", str(len(PAGE)))
        self.end_headers()
        self.wfile.write(PAGE)

    def log_message(self, *a):
        pass


srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), H)
threading.Thread(target=srv.serve_forever, daemon=True).start()
URL = f"http://127.0.0.1:{srv.server_address[1]}/page"

counts: collections.Counter = collections.Counter()
_orig_send = wsc.ClientConnection.send


async def counting_send(self, message, *a, **kw):
    try:
        m = json.loads(message)
        if m.get("method") == "Page.addScriptToEvaluateOnNewDocument":
            counts[m.get("sessionId")] += 1
    except Exception:
        pass
    return await _orig_send(self, message, *a, **kw)


wsc.ClientConnection.send = counting_send


async def run_mode(browser, mode):
    tab = await browser.get(URL, new_tab=True)
    # no send went to the new tab yet
    assert tab.session_id is None, tab.session_id
    if mode == "seq":
        await tab.evaluate("1")
        await tab.evaluate("2")
    elif mode == "gather":
        await asyncio.gather(tab.evaluate("1"), tab.evaluate("2"))
    elif mode == "localstorage":
        await tab.set_local_storage({"a": "1", "b": "2"})
    sid = tab.session_id
    # load the page again so the registered scripts run
    await tab.get(URL)
    await asyncio.sleep(0.5)
    title = await tab.evaluate("document.title")
    same = await tab.evaluate(
        "Element.prototype._attachShadow === Element.prototype.attachShadow"
    )
    print(
        f"mode={mode:13s} addScript sent={counts[sid]} title={title!r} "
        f"_attachShadow===attachShadow: {same}"
    )
    await tab.close()


async def main():
    browser = await zd.start(headless=True, expert=True)
    try:
        for mode in ("seq", "gather", "localstorage", "seq", "gather"):
            await asyncio.wait_for(run_mode(browser, mode), 60)
    finally:
        await browser.stop()
        srv.shutdown()


asyncio.run(main())
