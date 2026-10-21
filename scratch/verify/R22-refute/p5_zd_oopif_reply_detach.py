"""zendriver-level A1.5: command in flight on an ATTACHED OOPIF Tab while the parent removes
the <iframe>. Logs raw frames to tell 'Chrome answered successfully but caller got
target session was detached' from the legit case. Real headless Chromium."""
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
    out = collections.Counter(); wire = []
    ws = browser.connection.websocket
    orig = ws.recv
    async def rec(*a, **k):
        m = await orig(*a, **k); wire.append((time.perf_counter(), json.loads(m))); return m
    ws.recv = rec
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
            await frame.evaluate("1")  # attach + prepare
            assert frame.session_id
            sid = frame.session_id
            delay_us = [0, 100, 200, 400, 700, 1000][trial % 6]
            await browser.connection.websocket.send(json.dumps({"id": 10**6 + trial, "method": "Runtime.evaluate",
                "params": {"expression": "document.getElementById('f').remove()"}, "sessionId": tab.session_id}))
            t0 = time.perf_counter()
            while time.perf_counter() - t0 < delay_us / 1e6: pass
            start = len(wire)
            task = asyncio.create_task(frame.send(cdp.runtime.evaluate("40+2")))
            done, _ = await asyncio.wait({task}, timeout=3)
            await asyncio.sleep(0.1)
            if not done:
                out["HANG"] += 1; task.cancel(); continue
            replies = [(ts, m) for ts, m in wire[start:] if m.get("sessionId") == sid and "id" in m]
            dets = [ts for ts, m in wire[start:] if m.get("method") == "Target.detachedFromTarget" and m["params"].get("sessionId") == sid]
            ok_reply = [r for r in replies if "result" in r[1] and r[1]["result"].get("result", {}).get("value") == 42]
            try:
                v = task.result(); out[f"ok value={v[0].value}"] += 1
            except ProtocolException as e:
                first = str(e).splitlines()[0]
                if ok_reply and first == "target session was detached":
                    gap = round((dets[0] - ok_reply[0][0]) * 1e6) if dets else None
                    out["BUG: chrome replied 42, caller got 'target session was detached'"] += 1
                    print(f"  trial {trial} delay {delay_us}us: success reply then detach {gap}us later -> caller got ProtocolException")
                else:
                    out["ProtocolException (no success reply on wire): " + first[:50]] += 1
        print("outcomes:", dict(out))
    finally:
        await browser.stop(); srv.shutdown()

asyncio.run(main())
