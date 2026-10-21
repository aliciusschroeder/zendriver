"""B14.7 through the public API: tab.select(..., include_frames=True, timeout=1) on a page whose
cross-site iframe is replaced every few ms (ad-rotator style). Real headless Chromium.
A call that takes far longer than its own timeout is stuck."""
import asyncio, time, sys, threading, http.server, collections
import zendriver
print("zendriver from", zendriver.__file__, "py", sys.version.split()[0])
PERIOD = int(sys.argv[2]) if len(sys.argv) > 2 else 30

class H(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        port = self.server.server_address[1]
        if self.path.startswith("/child"):
            body = "<p>ad</p>"
        else:
            body = f"""<div id=box></div><script>
            let n=0; setInterval(() => {{ const b=document.getElementById('box'); b.innerHTML='';
              const f=document.createElement('iframe'); f.src='http://localhost:{port}/child?'+(n++); b.appendChild(f); }}, {PERIOD});
            </script>"""
        b = body.encode(); self.send_response(200); self.send_header("Content-Type", "text/html")
        self.send_header("Content-Length", str(len(b))); self.end_headers(); self.wfile.write(b)
    def log_message(self, *a): pass

N = int(sys.argv[1]) if len(sys.argv) > 1 else 10

async def main():
    srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), H)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    url = f"http://127.0.0.1:{srv.server_address[1]}/"
    browser = await zendriver.start(headless=True)
    out = collections.Counter()
    try:
        ws = browser.connection.websocket; orig = ws.send; cnt = collections.Counter()
        async def snd(m, *a, **k):
            if '"Target.attachToTarget"' in m: cnt["attach"] += 1
            return await orig(m, *a, **k)
        ws.send = snd
        tab = await browser.get(url)
        await asyncio.sleep(0.5)
        for i in range(N):
            t0 = time.perf_counter()
            task = asyncio.create_task(tab.select("#nope", include_frames=True, timeout=1))
            done, _ = await asyncio.wait({task}, timeout=15)
            dt = time.perf_counter() - t0
            if not done:
                out["STUCK >15s (select timeout=1)"] += 1
                task.print_stack(file=sys.stdout)
                task.cancel()
                try: await task
                except BaseException: pass
                continue
            try:
                task.result(); out["found?"] += 1
            except asyncio.TimeoutError:
                out["select TimeoutError as designed"] += 1
            except Exception as e:
                out[type(e).__name__ + ": " + str(e).splitlines()[0][:60]] += 1
        print(f"period={PERIOD}ms outcomes:", dict(out), "attach commands sent:", cnt["attach"])
    finally:
        await browser.stop(); srv.shutdown()

asyncio.run(main())
