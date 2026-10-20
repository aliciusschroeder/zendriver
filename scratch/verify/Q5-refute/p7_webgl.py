import array, asyncio, fcntl, os, sys, termios, time, re, collections, http.server, threading
import zendriver
print("zendriver from", zendriver.__file__, sys.version.split()[0], "headless", sys.argv[1], flush=True)
def pending(f):
    buf = array.array("i", [0]); fcntl.ioctl(f.fileno(), termios.FIONREAD, buf, True); return buf[0]
PAGES = {
 "plain": b"<html><body><h1>p</h1></body></html>",
 "webgl": b"<html><body><canvas id=c></canvas><script>document.getElementById('c').getContext('webgl')</script></body></html>",
 "webgl2": b"<html><body><canvas id=c></canvas><script>document.getElementById('c').getContext('webgl2')</script></body></html>",
 "canvas2d": b"<html><body><canvas id=c></canvas><script>document.getElementById('c').getContext('2d').fillText('x',1,1)</script></body></html>",
}
class H(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        body = PAGES[self.path.split('/')[1]]
        self.send_response(200); self.send_header("Content-Length", str(len(body))); self.end_headers(); self.wfile.write(body)
    def log_message(self,*a): pass
async def main():
    srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), H); threading.Thread(target=srv.serve_forever, daemon=True).start()
    port = srv.server_address[1]
    b = await zendriver.start(headless=sys.argv[1] == "1", browser_connection_max_tries=40)
    print("udd", b.config.user_data_dir, flush=True)
    await asyncio.sleep(2)
    for kind in ["plain", "canvas2d", "webgl", "webgl2"]:
        before = pending(b._process.stderr)
        for i in range(30):
            await asyncio.wait_for(b.main_tab.get(f"http://127.0.0.1:{port}/{kind}/{i}"), 20)
        await asyncio.sleep(0.5)
        print("%-9s 30 navs: +%d bytes (%.0f B/nav); pending %d" % (kind, pending(b._process.stderr)-before, (pending(b._process.stderr)-before)/30, pending(b._process.stderr)), flush=True)
    data = os.read(b._process.stderr.fileno(), 1<<20).decode("utf-8","replace")
    for l in data.splitlines():
        if "context_group" in l:
            print("sample:", l[:300], flush=True); break
    await asyncio.wait_for(b.stop(), 30)
    print("stopped", flush=True)
asyncio.run(main())
