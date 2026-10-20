import asyncio, http.server, threading, sys, logging
import zendriver as zd

MODE = sys.argv[1] if len(sys.argv) > 1 else "navigate"

PAGE = """<html><body>
<div id="host"></div>
<input type="hidden" name="cf-turnstile-response" value="">
<script>
const root = document.getElementById('host').attachShadow({mode:'closed'});
root.innerHTML = '<div id="w" data-src="https://challenges.cloudflare.com/turnstile" style="width:300px;height:65px;background:#eee"></div>';
root.getElementById('w').addEventListener('click', () => {
  if ("%s" === "navigate") { location.href = '/solved'; }
  else if ("%s" === "value") { document.querySelector('input[name=cf-turnstile-response]').value = 'tok'; }
  else if ("%s" === "remove") { document.querySelector('input[name=cf-turnstile-response]').remove(); }
});
</script>
</body></html>""" % (MODE, MODE, MODE)

class H(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        data = (PAGE if self.path == "/" else "<html><body><p>welcome, solved</p></body></html>").encode()
        self.send_response(200); self.send_header("Content-Type","text/html"); self.send_header("Content-Length", str(len(data))); self.end_headers(); self.wfile.write(data)
    def log_message(self, *a): pass

async def main():
    srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), H)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    browser = await zd.start(headless=True)
    try:
        tab = await browser.get(f"http://127.0.0.1:{srv.server_address[1]}/")
        await tab.sleep(1)
        t0 = asyncio.get_running_loop().time()
        try:
            await asyncio.wait_for(tab.verify_cf(click_delay=1, timeout=10), 40)
            print("MODE", MODE, "verify_cf returned OK after", round(asyncio.get_running_loop().time()-t0,2))
        except BaseException as e:
            print("MODE", MODE, "verify_cf raised", type(e).__name__, repr(e)[:300])
        print("final url", tab.target.url)
    finally:
        await browser.stop()
        srv.shutdown()

asyncio.run(main())
