"""Raw CDP: attach to an OOPIF iframe target while its <iframe> is being removed
by the parent; measure attach reply -> detachedFromTarget gap (real Chromium)."""
import asyncio, json, time, sys, threading, http.server
import websockets
import zendriver
print("zendriver from", zendriver.__file__, "py", sys.version.split()[0])

class H(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        port = self.server.server_address[1]
        if self.path.startswith("/child"):
            body = "<p>child</p>"
        else:
            body = f"<iframe id='f' src='http://localhost:{port}/child'></iframe>"
        b = body.encode(); self.send_response(200); self.send_header("Content-Type", "text/html")
        self.send_header("Content-Length", str(len(b))); self.end_headers(); self.wfile.write(b)
    def log_message(self, *a): pass

async def main():
    srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), H)
    th = threading.Thread(target=srv.serve_forever, daemon=True); th.start()
    url = f"http://127.0.0.1:{srv.server_address[1]}/"
    browser = await zendriver.start(headless=True)
    try:
        async with websockets.connect(browser.connection.websocket_url, max_size=2**26) as ws:
            n = [7000]; frames = []
            async def reader():
                while True:
                    raw = await ws.recv(); frames.append((time.perf_counter(), json.loads(raw)))
            rt = asyncio.create_task(reader())
            async def send(method, params, sid=None):
                n[0] += 1; msg = {"id": n[0], "method": method, "params": params}
                if sid: msg["sessionId"] = sid
                await ws.send(json.dumps(msg)); return n[0]
            async def call(method, params, sid=None):
                i = await send(method, params, sid)
                for _ in range(500):
                    for ts, m in frames:
                        if m.get("id") == i: return m
                    await asyncio.sleep(0.01)
            t = await call("Target.createTarget", {"url": "about:blank"})
            ptid = t["result"]["targetId"]
            psid = (await call("Target.attachToTarget", {"targetId": ptid, "flatten": True}))["result"]["sessionId"]
            await call("Page.enable", {}, psid)
            gaps = []
            for delay_us in [0, 0, 0, 200, 500, 1000, 2000, 0, 0, 0]:
                await call("Page.navigate", {"url": url + f"?{time.time()}"}, psid)
                ift = None
                for _ in range(100):
                    ts = (await call("Target.getTargets", {}))["result"]["targetInfos"]
                    ift = [x for x in ts if x["type"] == "iframe" and x.get("parentFrameId")]
                    if ift: break
                    await asyncio.sleep(0.05)
                itid = ift[0]["targetId"]
                start = len(frames)
                await send("Runtime.evaluate", {"expression": "document.getElementById('f').remove()"}, psid)
                t0 = time.perf_counter()
                while time.perf_counter() - t0 < delay_us / 1e6: pass
                a = await send("Target.attachToTarget", {"targetId": itid, "flatten": True})
                await asyncio.sleep(0.5)
                ra = [(ts, m) for ts, m in frames[start:] if m.get("id") == a][0]
                sid = ra[1].get("result", {}).get("sessionId")
                det = [ts for ts, m in frames[start:] if m.get("method") == "Target.detachedFromTarget" and m["params"].get("sessionId") == sid]
                g = round((det[0] - ra[0]) * 1000, 3) if det else None
                print(f"delay {delay_us}us: attach ->", "sessionId" if sid else ra[1].get("error"), "detach gap ms:", g)
            rt.cancel()
    finally:
        await browser.stop(); srv.shutdown()

asyncio.run(main())
