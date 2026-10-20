"""Default zendriver flags, headless: load pages that create a WebGL context until the
stderr pipe fills; then check which APIs still answer."""
import array
import asyncio
import fcntl
import http.server
import os
import sys
import termios
import threading
import time

import psutil
import zendriver

print("zendriver from", zendriver.__file__, sys.version.split()[0], "headless", sys.argv[1], flush=True)
DRAIN = len(sys.argv) > 2 and sys.argv[2] == "drain"


def pending(f) -> int:
    buf = array.array("i", [0])
    fcntl.ioctl(f.fileno(), termios.FIONREAD, buf, True)
    return buf[0]


PAGE = b"<html><body><canvas id=c></canvas><script>document.getElementById('c').getContext('webgl')</script><h1>w</h1></body></html>"
PLAIN = b"<html><body><h1>plain</h1></body></html>"


class H(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        body = PLAIN if self.path.startswith("/plain") else PAGE
        self.send_response(200)
        self.send_header("Content-Type", "text/html")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *a):
        pass


def pipe_writers(root_pid: int):
    out = []
    try:
        procs = [psutil.Process(root_pid)] + psutil.Process(root_pid).children(recursive=True)
    except psutil.Error:
        return out
    for p in procs:
        try:
            for tid in os.listdir(f"/proc/{p.pid}/task"):
                w = open(f"/proc/{p.pid}/task/{tid}/wchan").read()
                if w == "anon_pipe_write":
                    comm = open(f"/proc/{p.pid}/task/{tid}/comm").read().strip()
                    ptype = next((a for a in p.cmdline() if a.startswith("--type=")), "--type=browser")
                    out.append((p.pid, comm, ptype))
        except (OSError, psutil.Error):
            pass
    return out


async def main() -> None:
    srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), H)
    srv.handle_error = lambda *a: None
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    port = srv.server_address[1]
    b = await zendriver.start(headless=sys.argv[1] == "1", browser_connection_max_tries=40)
    proc = b._process
    print("udd", b.config.user_data_dir, flush=True)
    drained = [0]
    if DRAIN:
        def drain():
            while True:
                d = os.read(proc.stderr.fileno(), 65536)
                if not d:
                    return
                drained[0] += len(d)
        threading.Thread(target=drain, daemon=True).start()
    tab = b.main_tab
    t0 = time.monotonic()
    hung = False
    for i in range(400):
        try:
            await asyncio.wait_for(tab.get(f"http://127.0.0.1:{port}/w{i}"), 15)
        except asyncio.TimeoutError:
            print("nav %d: tab.get TIMEOUT after %.0fs of browsing; stderr pending %d" % (i, time.monotonic() - t0, pending(proc.stderr)), flush=True)
            hung = True
            break
        if i % 25 == 0:
            print("nav %d ok; stderr pending %d drained %d" % (i, pending(proc.stderr), drained[0]), flush=True)
    print("hung=%s; blocked writers: %s" % (hung, pipe_writers(proc.pid)), flush=True)
    if hung:
        for label, fn in [
            ("evaluate 1+1", lambda: tab.evaluate("1+1")),
            ("Browser.getVersion", lambda: b.connection.send(zendriver.cdp.browser.get_version())),
            ("tab.get plain page", lambda: tab.get(f"http://127.0.0.1:{port}/plain")),
            ("screenshot", lambda: tab.screenshot_b64()),
            ("new tab", lambda: b.get(f"http://127.0.0.1:{port}/plain2", new_tab=True)),
        ]:
            try:
                await asyncio.wait_for(fn(), 10)
                print("  %s: OK" % label, flush=True)
            except asyncio.TimeoutError:
                print("  %s: TIMEOUT" % label, flush=True)
            except Exception as e:
                print("  %s: %r" % (label, e), flush=True)
        print("blocked writers now: %s" % pipe_writers(proc.pid), flush=True)
    st = asyncio.ensure_future(b.stop())
    done, _ = await asyncio.wait({st}, timeout=30)
    print("stop done=%s" % bool(done), flush=True)
    if not done:
        st.print_stack()
        for c in psutil.Process(proc.pid).children(recursive=True):
            c.kill()
        os.kill(proc.pid, 9)
        try:
            await asyncio.wait_for(st, 15)
        except BaseException as e:
            print("stop after kill:", repr(e), flush=True)
    if hung:
        data = os.read(proc.stderr.fileno(), 1 << 20).decode("utf-8", "replace")
        import collections, re
        print(collections.Counter(re.findall(r":(?:ERROR|WARNING):([^\]]+)\]", data)).most_common(8), flush=True)
    print("udd exists:", os.path.exists(b.config.user_data_dir), flush=True)


asyncio.run(main())
