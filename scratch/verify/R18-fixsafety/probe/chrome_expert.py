import asyncio, sys, threading, http.server
import zendriver as zd
print("zendriver from", zd.__file__, "python", sys.version.split()[0])

CHECK = """(() => { try { const d = document.createElement('div');
  d.attachShadow({mode: 'closed'}); return 'OK open=' + (d.shadowRoot !== null) }
  catch (e) { return 'ERR:' + e } })()"""

class H(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        body = b"<html><head><title>t</title></head><body>hi</body></html>"
        self.send_response(200); self.send_header("Content-Type", "text/html")
        self.send_header("Content-Length", str(len(body))); self.end_headers(); self.wfile.write(body)
    def log_message(self, *a): pass

srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), H)
threading.Thread(target=srv.serve_forever, daemon=True).start()
URL = f"http://127.0.0.1:{srv.server_address[1]}/"

async def run(mode):
    browser = await zd.start(headless=True, expert=True)
    try:
        tab = await browser.get(URL, new_tab=True)
        if mode == "gather":
            await asyncio.wait_for(asyncio.gather(tab.evaluate("1"), tab.evaluate("2")), 20)
        elif mode == "local_storage":
            await asyncio.wait_for(tab.set_local_storage({"a": "1", "b": "2"}), 20)
        else:
            await asyncio.wait_for(tab.evaluate("1"), 20)
            await asyncio.wait_for(tab.evaluate("2"), 20)
        await asyncio.wait_for(tab.get(URL + "?2"), 20)
        await asyncio.sleep(0.5)
        result = await asyncio.wait_for(tab.evaluate(CHECK), 20)
        print(f"{mode:14s} -> {result}")
    finally:
        await browser.stop()

async def main():
    for mode in sys.argv[1:]:
        await run(mode)
    srv.shutdown()

asyncio.run(main())
