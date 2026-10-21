"""Extra check of the B14.6 side claim: _prepare_expert has the same
flag-after-await pattern. Detach while the Page.enable oneshot of
_prepare_expert is pending, then reattach and see whether the expert
attachShadow override is applied to the new session.

Usage: python repro_expert_detach.py <race 0|1>
"""
import asyncio
import http.server
import sys
import threading

import zendriver as zd

print("zendriver from", zd.__file__, "python", sys.version.split()[0])
RACE = int(sys.argv[1])

PAGE = b"""<!doctype html><html><head><title>init</title></head><body><script>
const d = document.createElement('div'); document.body.appendChild(d);
d.attachShadow({mode: 'closed'});
document.title = d.shadowRoot ? 'OPEN(expert applied)' : 'CLOSED(expert not applied)';
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
URL = f"http://127.0.0.1:{srv.server_address[1]}/p"


async def main():
    browser = await zd.start(headless=True, expert=True)
    try:
        tab = await browser.get("about:blank", new_tab=True)
        if RACE:

            async def closer():
                while not any(
                    tx.method == "Page.enable" for tx in list(tab.mapper.values())
                ):
                    await asyncio.sleep(0)
                await tab.aclose()

            res = await asyncio.wait_for(
                asyncio.gather(tab.evaluate("1"), closer(), return_exceptions=True), 30
            )
            print("first send result:", [repr(r)[:80] for r in res])
        else:
            await tab.evaluate("1")
            await tab.aclose()
        print("after detach _prep_expert_done =", tab.__dict__.get("_prep_expert_done"))
        await asyncio.wait_for(tab.get(URL), 30)
        await asyncio.sleep(0.3)
        print("title after reattach:", await asyncio.wait_for(tab.evaluate("document.title"), 30))
        await tab.close()
    finally:
        await browser.stop()
        srv.shutdown()


asyncio.run(main())
