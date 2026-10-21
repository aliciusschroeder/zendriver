import asyncio, sys, threading, http.server
import zendriver as zd
print("zendriver from", zd.__file__)
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
async def main():
    browser = await zd.start(headless=True, expert=True)
    try:
        tab = await browser.get(URL, new_tab=True)
        await asyncio.wait_for(tab.evaluate("1"), 20)
        s1 = tab.session_id
        await asyncio.wait_for(tab.aclose(), 20)
        await asyncio.wait_for(tab.get(URL + "?2"), 20)  # reattaches, prepares the new session
        await asyncio.sleep(0.3)
        print("sessions", s1 != tab.session_id, "after reattach + reload:", await asyncio.wait_for(tab.evaluate(CHECK), 20))
    finally:
        await browser.stop()
    srv.shutdown()
asyncio.run(main())
