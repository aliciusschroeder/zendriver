import asyncio, sys, threading, http.server, time
import zendriver
print("zendriver from", zendriver.__file__, "python", sys.version.split()[0])

MODE = sys.argv[1] if len(sys.argv) > 1 else "navigate"
ACTIONS = {
    "navigate": "location.href='/solved';",
    "remove": "document.querySelector('input[name=cf-turnstile-response]').remove();",
    "value": "document.querySelector('input[name=cf-turnstile-response]').setAttribute('value','tok');",
}
PAGE = f"""<!doctype html><html><body style="margin:0">
<div id="host" style="width:320px;height:80px"></div>
<input type="hidden" name="cf-turnstile-response" value="">
<script>
const h = document.getElementById('host');
const sr = h.attachShadow({{mode:'closed'}});
const d = document.createElement('div');
d.setAttribute('data-src','https://challenges.cloudflare.com/x');
d.style.cssText='width:300px;height:65px;background:#ddd';
d.addEventListener('click', () => {{ {ACTIONS[MODE]} }});
sr.appendChild(d);
</script></body></html>"""

class H(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        body = (PAGE if self.path == "/" else "<html><body>solved real site</body></html>").encode()
        self.send_response(200); self.send_header("Content-Type", "text/html")
        self.send_header("Content-Length", str(len(body))); self.end_headers(); self.wfile.write(body)
    def log_message(self, *a): pass

srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), H)
threading.Thread(target=srv.serve_forever, daemon=True).start()
base = f"http://127.0.0.1:{srv.server_address[1]}"

async def main():
    browser = await zendriver.start(headless=True)
    try:
        tab = await browser.get(base + "/")
        await asyncio.sleep(1)
        t0 = time.monotonic()
        try:
            await asyncio.wait_for(tab.verify_cf(click_delay=1, timeout=10), 30)
            print(f"MODE={MODE}: verify_cf returned OK after {time.monotonic()-t0:.2f}s")
        except BaseException as e:
            print(f"MODE={MODE}: verify_cf RAISED {type(e).__name__}: {e!s:.300}")
        await tab
        print("final url:", tab.url)
    finally:
        await browser.stop()
        srv.shutdown()

asyncio.run(main())
