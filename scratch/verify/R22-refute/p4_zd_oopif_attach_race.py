"""zendriver-level: first send on an (unattached) OOPIF Tab while the parent removes the
<iframe>. Real headless Chromium, no loop blocking. Counts outcomes."""
import asyncio, json, time, sys, threading, http.server, collections
import zendriver
from zendriver import cdp
from zendriver.core.connection import ProtocolException
print("zendriver from", zendriver.__file__, "py", sys.version.split()[0])

class H(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        port = self.server.server_address[1]
        body = "<p>child</p>" if self.path.startswith("/child") else f"<iframe id='f' src='http://localhost:{port}/child'></iframe>"
        b = body.encode(); self.send_response(200); self.send_header("Content-Type", "text/html")
        self.send_header("Content-Length", str(len(b))); self.end_headers(); self.wfile.write(b)
    def log_message(self, *a): pass

TRIALS = int(sys.argv[1]) if len(sys.argv) > 1 else 30

async def main():
    srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), H)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    url = f"http://127.0.0.1:{srv.server_address[1]}/"
    browser = await zendriver.start(headless=True)
    outcomes = collections.Counter(); printed = False
    try:
        tab = await browser.get("about:blank")
        await tab.evaluate("1")
        for trial in range(TRIALS):
            await tab.send(cdp.page.navigate(url + f"?{trial}"))
            frame = None
            for _ in range(100):
                await browser.update_targets()
                fr = [t for t in browser.targets if getattr(t, "type_", None) == "iframe" and t.session_id is None]
                if fr: frame = fr[-1]; break
                await asyncio.sleep(0.05)
            assert frame is not None
            delay_us = [0, 100, 200, 300, 500][trial % 5]
            # ask the parent to remove the iframe, without waiting for the reply
            await browser.connection.websocket.send(json.dumps({"id": 10**6 + trial, "method": "Runtime.evaluate",
                "params": {"expression": "document.getElementById('f').remove()"}, "sessionId": tab.session_id}))
            t0 = time.perf_counter()
            while time.perf_counter() - t0 < delay_us / 1e6: pass
            task = asyncio.create_task(frame.send(cdp.runtime.evaluate("1+1")))
            done, _ = await asyncio.wait({task}, timeout=3)
            if not done:
                outcomes["HANG"] += 1
                if not printed:
                    printed = True
                    print("HANG: frame.session_id=", frame.session_id,
                          "registered in browser._sessions:", frame.session_id in browser.connection._sessions,
                          "frame mapper ids:", list(frame.mapper), "browser mapper ids:", list(browser.connection.mapper))
                    task.print_stack(file=sys.stdout)
                task.cancel()
                try: await task
                except BaseException: pass
            else:
                try:
                    task.result(); outcomes["ok"] += 1
                except ProtocolException as e:
                    outcomes["ProtocolException: " + str(e).splitlines()[0][:60]] += 1
                except Exception as e:
                    outcomes[type(e).__name__ + ": " + str(e)[:60]] += 1
        print("outcomes:", dict(outcomes))
    finally:
        await browser.stop(); srv.shutdown()

asyncio.run(main())
