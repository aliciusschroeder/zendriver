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
        task = asyncio.create_task(tab.evaluate("1"))
        while tab.session_id is None:
            await asyncio.sleep(0)
        await asyncio.sleep(0)
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            print("first send cancelled; expert flag:", tab.__dict__.get("_prep_expert_done"))
        await asyncio.wait_for(tab.get(URL + "?2"), 20)
        await asyncio.sleep(0.3)
        print("after reload:", await asyncio.wait_for(tab.evaluate(CHECK), 20))
    finally:
        await browser.stop()
    srv.shutdown()
asyncio.run(main())
