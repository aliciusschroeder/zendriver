import array, asyncio, fcntl, os, sys, termios, time, re, collections, http.server, threading
import zendriver, logging
logging.basicConfig(level=logging.WARNING); logging.getLogger("zendriver.core.browser").setLevel(logging.INFO)
print("zendriver from", zendriver.__file__, sys.version.split()[0], "DISPLAY", os.environ.get("DISPLAY"), flush=True)
def pending(f):
    buf = array.array("i", [0]); fcntl.ioctl(f.fileno(), termios.FIONREAD, buf, True); return buf[0]
class H(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        body = b"<html><body><canvas id=c></canvas><script>const g=document.getElementById('c').getContext('webgl'); console.log('hi')</script><h1>p</h1></body></html>"
        self.send_response(200); self.send_header("Content-Length", str(len(body))); self.end_headers(); self.wfile.write(body)
    def log_message(self,*a): pass
async def main():
    srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), H); threading.Thread(target=srv.serve_forever, daemon=True).start()
    port = srv.server_address[1]
    t0=time.monotonic()
    try:
        b = await zendriver.start(headless=False, browser_connection_max_tries=int(sys.argv[1]))
    except Exception as e:
        print("start failed after %.1fs" % (time.monotonic()-t0), flush=True); return
    print("started in %.1fs" % (time.monotonic()-t0), flush=True)
    print("udd", b.config.user_data_dir, flush=True)
    await asyncio.sleep(3)
    print("headful after start+3s: stderr pending", pending(b._process.stderr), flush=True)
    t = time.monotonic()
    for i in range(60):
        await asyncio.wait_for(b.main_tab.get(f"http://127.0.0.1:{port}/p{i}"), 20)
    print("after 60 navigations (%.0fs): stderr pending %d" % (time.monotonic()-t, pending(b._process.stderr)), flush=True)
    for i in range(10):
        tb = await asyncio.wait_for(b.get(f"http://127.0.0.1:{port}/n{i}", new_tab=True), 20)
        await tb.close()
    print("after 10 new tabs: stderr pending %d" % pending(b._process.stderr), flush=True)
    await asyncio.sleep(60)
    print("after 60s idle: stderr pending %d" % pending(b._process.stderr), flush=True)
    data = os.read(b._process.stderr.fileno(), 1<<20).decode("utf-8","replace")
    c = collections.Counter(re.findall(r":(?:ERROR|WARNING|INFO):([^\]]+)\]", data))
    print(c.most_common(12), flush=True)
    await asyncio.wait_for(b.stop(), 30)
    print("stopped", flush=True)
asyncio.run(main())
