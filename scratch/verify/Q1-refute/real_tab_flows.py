import asyncio, sys, http.server, threading
import zendriver
from zendriver import cdp
print("zendriver from", zendriver.__file__, "python", sys.version.split()[0])

class H(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200); self.send_header("Content-Type", "text/html"); self.end_headers()
        self.wfile.write(b"<html><body><img src='/img.png'>hi</body></html>")
    def log_message(self, *a): pass

async def step(label, coro, t=5):
    task = asyncio.ensure_future(coro)
    done, _ = await asyncio.wait({task}, timeout=t)
    if not done:
        print(f"{label}: HUNG ({t}s)"); task.print_stack(limit=1, file=sys.stdout); sys.stdout.flush()
        task.cancel(); await asyncio.gather(task, return_exceptions=True); return
    exc = task.exception()
    print(f"{label}: {'raised ' + type(exc).__name__ + ': ' + str(exc)[:70] if exc else 'ok -> ' + repr(task.result())[:50]}")

def custom_cmd():
    j = yield {"method": "Runtime.evaluate", "params": {"expression": "1"}}
    return j["notThere"]

async def main():
    srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), H)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    url = f"http://127.0.0.1:{srv.server_address[1]}/"
    browser = await zendriver.start(headless=True)
    try:
        tab = browser.main_tab
        # A2.3: custom generator on a real tab
        await step("A2.3 custom generator tab.send", tab.send(custom_cmd()))
        print("   tab listener running:", tab.listener.running, "browser listener running:", browser.connection.listener.running)
        await step("   next tab.evaluate (send revives tab listener)", tab.evaluate("1+1"))
        # B15.4 on a tab with a realistic event: wrong-arity async handler on RequestWillBeSent
        async def on_request():  # forgot the event parameter
            pass
        tab.add_handler(cdp.network.RequestWillBeSent, on_request)
        await step("B15.4 tab.send(page.navigate) w/ bad RequestWillBeSent handler", tab.send(cdp.page.navigate(url)), 8)
        print("   tab listener running:", tab.listener.running)
        await step("B15.4 tab.get(url) (wait_for 10s inside)", tab.get(url), 15)
        print("   tab listener running:", tab.listener.running)
        tab.remove_handlers(cdp.network.RequestWillBeSent, on_request)
        await step("   tab.evaluate after removing bad handler", tab.evaluate("2+2"))
    finally:
        await asyncio.wait_for(browser.stop(), 20)
        srv.shutdown()
asyncio.run(asyncio.wait_for(main(), 100))
