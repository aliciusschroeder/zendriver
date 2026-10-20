import asyncio, threading, http.server, sys
import zendriver as zd
from zendriver import cdp

class H(http.server.BaseHTTPRequestHandler):
    def log_message(self, *a): pass
    def do_GET(self):
        body = b"<html><script>alert('hi')</script>after</html>"
        self.send_response(200); self.send_header("Content-Type", "text/html"); self.send_header("Content-Length", str(len(body))); self.end_headers(); self.wfile.write(body)

async def main():
    srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), H)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    base = f"http://127.0.0.1:{srv.server_address[1]}"
    browser = await zd.start(headless=True, expert=("expert" in sys.argv))
    if "fallback" in sys.argv:
        browser._headless_user_agent = None
    try:
        tab = await browser.get(base + "/alert", new_tab=True)
        await asyncio.sleep(1)
        if "skipprep" in sys.argv:
            tab._prep_headless_done = True
        if "pageenable" in sys.argv:
            await asyncio.wait_for(tab.send(cdp.page.enable()), 5)
            print("page.enable ok")
        t = asyncio.create_task(tab.send(cdp.page.handle_java_script_dialog(accept=True)))
        await asyncio.sleep(3)
        if not t.done():
            for f in t.get_stack(limit=30): print("  stuck at", f.f_code.co_name, f.f_lineno)
        try:
            await asyncio.wait_for(t, 3)
            print("dialog handled ok")
            print("evaluate after:", await asyncio.wait_for(tab.evaluate("document.body.innerText"), 5))
        except asyncio.TimeoutError:
            print("HUNG: first send to a tab with an open dialog")
        except Exception as e:
            print("raised", type(e).__name__, e)
    finally:
        await browser.stop()

asyncio.run(asyncio.wait_for(main(), 50))
