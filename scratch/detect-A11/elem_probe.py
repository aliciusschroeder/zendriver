import asyncio, http.server, threading
import zendriver as zd

PAGE = """<html><body>
<p id="p1">line one<br clear="all" id="b">line two</p>
<a id="a1" href="/x" items="3">link</a>
<span id="s" get="g">t</span>
<svg><animate id="an" attributeName="opacity" values="0;1;0" dur="1s"/></svg>
</body></html>"""

class H(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        data = PAGE.encode()
        self.send_response(200); self.send_header("Content-Type","text/html"); self.send_header("Content-Length", str(len(data))); self.end_headers(); self.wfile.write(data)
    def log_message(self, *a): pass

async def step(label, coro_fn):
    try:
        r = await asyncio.wait_for(coro_fn(), 20)
        print(label, "-> OK", repr(r)[:120])
    except Exception as e:
        print(label, "-> RAISES", type(e).__name__, str(e)[:150])

async def main():
    srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), H)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    browser = await zd.start(headless=True)
    try:
        tab = await browser.get(f"http://127.0.0.1:{srv.server_address[1]}/")
        await tab.sleep(0.5)
        br = await tab.select("#b")
        await step("await br (update)", lambda: br.update())
        await step("br.query_selector('x')", lambda: br.query_selector("x"))
        p1 = await tab.select("#p1")
        await step("p1 update (parent of br) ", lambda: p1.update())
        await step("p1.query_selector('#b')", lambda: p1.query_selector("#b"))
        await step("repr(p1) (child br has clear)", lambda: asyncio.sleep(0, repr(p1)))
        a1 = await tab.select("#a1")
        await step("repr(a1)", lambda: asyncio.sleep(0, repr(a1)))
        await step("tab.get_all_urls()", lambda: tab.get_all_urls())
        s = await tab.select("#s")
        await step("s.get('id')", lambda: asyncio.sleep(0, s.get("id")))
        await step("s['id']", lambda: asyncio.sleep(0, s["id"]))
        await step("s.id via __getattr__", lambda: asyncio.sleep(0, s.id))
        an = await tab.select("#an")
        await step("an.attrs.values()", lambda: asyncio.sleep(0, list(an.attrs.values())))
    finally:
        await browser.stop()
        srv.shutdown()

asyncio.run(main())
